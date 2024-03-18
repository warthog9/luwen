// SPDX-FileCopyrightText: © 2023 Tenstorrent Inc.
// SPDX-License-Identifier: Apache-2.0

use std::convert::Infallible;

use indicatif::ProgressBar;
use ttkmd_if::PciDevice;
use luwen_if::{
    chip::{
        Chip, ChipDetectState, CommsStatus, ComponentStatusInfo, HlCommsInterface, InitError,
        InitStatus,
    },
    CallbackStorage, ChipDetectOptions, UninitChip,
};

use crate::{comms_callback, error::LuwenError, ExtendedPciDevice};

pub fn detect_chips_fallible() -> Result<Vec<UninitChip>, LuwenError> {
    let mut chips = Vec::new();
    let mut failed_chips = Vec::new();

    let device_ids = PciDevice::scan();
    for device_id in device_ids {
        let ud = ExtendedPciDevice::open(device_id)?;

        let arch = ud.borrow().device.arch;

        let chip = Chip::open(arch, CallbackStorage::new(comms_callback, ud.clone()))?;

        // First let's test basic pcie communication we may be in a hang state so it's
        // important that we let the detect function know
        let result = chip.axi_sread32("ARC_RESET.SCRATCH[0]");
        if let Err(err) = result {
            // Basic comms have failed... we should output a nice error message on the console
            failed_chips.push((device_id, chip, err));
        } else {
            chips.push(chip);
        }
    }

    let chip_detect_bar = indicatif::ProgressBar::new_spinner().with_style(
        indicatif::ProgressStyle::default_spinner()
            .template("{spinner:.green} Detecting chips (found {pos})")
            .unwrap(),
    );

    let mut chip_init_bar = None;
    let mut arc_init_bar = None;
    let mut dram_init_bar = None;
    let mut eth_init_bar = None;
    let mut cpu_init_bar = None;

    fn add_bar(bars: &indicatif::MultiProgress) -> ProgressBar {
        let new_bar = bars.add(
            indicatif::ProgressBar::new_spinner().with_style(
                indicatif::ProgressStyle::default_spinner()
                    .template("{spinner:.green} {msg}")
                    .unwrap(),
            ),
        );
        new_bar.set_message("Initializing Chip");
        new_bar.enable_steady_tick(std::time::Duration::from_secs_f32(1.0 / 30.0));

        new_bar
    }

    fn update_bar_with_status<P: std::fmt::Display, E: std::fmt::Display>(
        bars: &indicatif::MultiProgress,
        bar: &mut Option<ProgressBar>,
        status: &ComponentStatusInfo<P, E>,
    ) {
        if bar.is_none() && status.is_present() {
            *bar = Some(add_bar(bars));
        }

        if let Some(bar) = bar {
            if status.is_waiting() && status.is_present() {
                bar.set_message(status.to_string());
            }
        }
    }

    fn maybe_remove_bar<P, E>(
        bars: &indicatif::MultiProgress,
        bar: &mut Option<ProgressBar>,
        status: &ComponentStatusInfo<P, E>,
    ) {
        if let Some(bar) = bar.take() {
            if status.has_error() {
                bar.finish();
            } else {
                bar.finish_and_clear();
                bars.remove(&bar);
            }
        }
    }

    let bars = indicatif::MultiProgress::new();
    let chip_detect_bar = bars.add(chip_detect_bar);
    chip_detect_bar.enable_steady_tick(std::time::Duration::from_secs_f32(1.0 / 30.0));

    // First we will output errors for the chips we alraedy know have failed
    for (id, _, err) in &failed_chips {
        chip_detect_bar.inc(1);
        let bar = add_bar(&bars);
        bar.finish_with_message(format!(
            "Failed to communicate over pcie with chip {id}: {err}"
        ));
    }

    let mut init_callback = |status: ChipDetectState| {
        match status.call {
            luwen_if::chip::CallReason::NotNew => {
                chip_detect_bar.set_position(chip_detect_bar.position().saturating_sub(1));
            }
            luwen_if::chip::CallReason::NewChip => {
                chip_detect_bar.inc(1);
                chip_init_bar = Some(add_bar(&bars));
            }
            luwen_if::chip::CallReason::InitWait(status) => {
                update_bar_with_status(&bars, &mut arc_init_bar, &status.arc_status);
                update_bar_with_status(&bars, &mut dram_init_bar, &status.dram_status);
                update_bar_with_status(&bars, &mut eth_init_bar, &status.eth_status);
                update_bar_with_status(&bars, &mut cpu_init_bar, &status.cpu_status);

                if let Some(bar) = chip_init_bar.as_ref() {
                    bar.set_message(format!("Waiting chip to initialize"));
                }
            }
            luwen_if::chip::CallReason::ChipInitCompleted(status) => {
                chip_detect_bar.set_message("Chip initialization complete (found {pos})");

                maybe_remove_bar(&bars, &mut arc_init_bar, &status.arc_status);
                maybe_remove_bar(&bars, &mut dram_init_bar, &status.dram_status);
                maybe_remove_bar(&bars, &mut eth_init_bar, &status.eth_status);
                maybe_remove_bar(&bars, &mut cpu_init_bar, &status.cpu_status);

                if let Some(bar) = chip_init_bar.take() {
                    if status.has_error() {
                        bar.finish_with_message("Chip initialization failed");
                    } else {
                        bar.finish_and_clear();
                        bars.remove(&bar);
                    }
                }
            }
        };

        Ok::<(), Infallible>(())
    };

    let options = ChipDetectOptions::default();
    let mut chips = match luwen_if::detect_chips(chips, &mut init_callback, options) {
        Err(InitError::CallbackError(err)) => {
            chip_detect_bar
                .finish_with_message(format!("Ran into error from status callback;\n{}", err));
            return Err(luwen_if::error::PlatformError::Generic(
                "Hit error from status callback".to_string(),
                luwen_if::error::BtWrapper::capture(),
            ))?;
        }
        Err(InitError::PlatformError(err)) => {
            return Err(err)?;
        }

        Ok(chips) => chips,
    };

    chip_detect_bar.finish_with_message("Chip detection complete (found {pos})");

    for (id, chip, err) in failed_chips.into_iter() {
        let mut status = InitStatus::new_unknown();
        status.comms_status = CommsStatus::CommunicationError(err.to_string());
        status.unknown_state = false;
        chips.insert(
            id,
            UninitChip::Partially {
                status,
                underlying: chip,
            },
        );
    }

    println!("");

    Ok(chips)
}

pub fn detect_chips() -> Result<Vec<Chip>, LuwenError> {
    let chips = detect_chips_fallible()?;

    let mut output = Vec::with_capacity(chips.len());
    for chip in chips {
        output.push(chip.init(&mut |_| Ok::<(), Infallible>(())).map_err(Into::<luwen_if::error::PlatformError>::into)?);
    }

    Ok(output)
}
