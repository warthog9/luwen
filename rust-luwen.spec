%bcond_without check
#% bcond_with check

%global crate luwen
%global path_luwen_if %{cargo_registry}/luwen-if-%{version_no_tilde}
%global path_luwen_ref %{cargo_registry}/luwen-ref-%{version_no_tilde}
%global path_ttkmd_if %{cargo_registry}/ttkmd-if-%{version_no_tilde}

Name:           rust-luwen
Version:        0.4.8
Release:        %autorelease.git.1.499b83b
Summary:        High-level interface for safe and efficient access Tenstorrent AI accelerators

License:        Apache-2.0
URL:            https://crates.io/crates/luwen
Source: rust-luwen-git-142.499b83b.tar.gz

BuildRequires:  cargo-rpm-macros >= 24
BuildRequires:  python%{python3_pkgversion}-devel
#BuildRequires:  rust-bincode+default-devel
#BuildRequires:  rust-bitfield+default-devel
#BuildRequires:  rust-cbindgen+default-devel
#BuildRequires:  rust-clap+default-devel
#BuildRequires:  rust-clap+derive-devel
#BuildRequires:  rust-indicatif+default-devel
#BuildRequires:  rust-memmap2+default-devel
#BuildRequires:  rust-nix+default-devel
#BuildRequires:  rust-nom+default-devel
#BuildRequires:  rust-once_cell+default-devel
#BuildRequires:  rust-prometheus+default-devel
#BuildRequires:  rust-prometheus+process-devel
#BuildRequires:  rust-pyo3+default-devel
#BuildRequires:  rust-pyo3+extension-module-devel
#BuildRequires:  rust-pyo3+multiple-pymethods-devel
#BuildRequires:  rust-rand+default-devel
#BuildRequires:  rust-rust-embed+default-devel
#BuildRequires:  rust-rust-embed+interpolate-folder-path-devel
#BuildRequires:  rust-serde+default-devel
#BuildRequires:  rust-serde+derive-devel
#BuildRequires:  rust-serde_yaml+default-devel
#BuildRequires:  rust-thiserror+default-devel
#BuildRequires:  rust-tracing+default-devel
#BuildRequires:  rust-memmap2_0.7+default-devel
#BuildRequires:  rust-nix0.26+default-devel
#BuildRequires:  rust-pyo3_0.19+default-devel
#BuildRequires:  rust-pyo3_0.19+extension-module-devel
#BuildRequires:  rust-pyo3_0.19+multiple-pymethods-devel

# we need to manipulate the Cargo.toml files in flight
BuildRequires:  tomcli
BuildRequires:  maturin

%global _description %{expand:
A high-level interface for safe and efficient access Tenstorrent AI
accelerators.}

%description
%{_description}

%package     -n %{crate}
Summary:        %{summary}
# FIXME: paste output of %%cargo_license_summary here
#License:        # FIXME
License:        Apache-2.0
# LICENSE.dependencies contains a full license breakdown

%description -n %{crate}
%{_description}

%files       -n %{crate}
%license LICENSE
%license LICENSE.dependencies
%doc README.md
%doc SUMMARY.md
%doc TODO.md
%{_bindir}/detect_test
%{_bindir}/druken_monkey
%{_bindir}/ethernet_benchmark
%{_bindir}/generate_names
%{_bindir}/luwen-cem
%{_bindir}/luwen-demo
%{_bindir}/reset-test
%{_bindir}/spi-test

############################
# rust-luwen-if
############################

%package     -n rust-luwen-if-devel
Summary:        Python bindings for the Tenstorrent Luwen library

%description -n rust-luwen-if-devel

This package contains library source intended for building other packages which
use the "internal_metrics" feature of the "%{crate}" crate.

%files       -n rust-luwen-if-devel
%{cargo_registry}/luwen-if-%{version_no_tilde}

############################
# rust-luwen-ref
############################

%package     -n rust-luwen-ref-devel
Summary:        Python bindings for the Tenstorrent Luwen library

%description -n rust-luwen-ref-devel

This package contains library source intended for building other packages which
use the "internal_metrics" feature of the "%{crate}" crate.

%files       -n rust-luwen-ref-devel
%{cargo_registry}/luwen-ref-%{version_no_tilde}

############################
# rust-ttkmd-if
############################

%package     -n rust-ttkmd-if-devel
Summary:        Python bindings for the Tenstorrent Luwen library

%description -n rust-ttkmd-if-devel

This package contains library source intended for building other packages which
use the "internal_metrics" feature of the "%{crate}" crate.

%files       -n rust-ttkmd-if-devel
%{cargo_registry}/ttkmd-if-%{version_no_tilde}

############################
# PyLuwen
############################

%package     -n python3-pyluwen
Summary:        Python bindings for the Tenstorrent Luwen library

%description -n python3-pyluwen
%{_description}

This package contains library source intended for building other packages which
use the "internal_metrics" feature of the "%{crate}" crate.

%files       -n python3-pyluwen
%{python3_sitearch}/pyluwen-*.dist-info
%{python3_sitearch}/pyluwen/

############################
# Main package
############################

%prep
%autosetup -p1 -n rust-luwen-git-142.499b83b -p1
%cargo_prep

%generate_buildrequires
%cargo_generate_buildrequires

%build
# This builds everything but luwencpp and pyluwen, the former has a bug, the later we build independently
%cargo_build '--workspace' '--exclude' 'luwencpp' '--exclude' 'pyluwen'
%{cargo_license_summary}
%{cargo_license} > LICENSE.dependencies

# build pyluwen
cd crates/pyluwen
CFLAGS="${CFLAGS:-${RPM_OPT_FLAGS}}" \
LDFLAGS="${LDFLAGS:-${RPM_LD_FLAGS}}" \
maturin build --release %{?py_setup_args} %{?*}

%install
%cargo_install
#%{__cp} -av LICENSE % {crate_instdir}/LICENSE
#%{__cp} -av README.md % {crate_instdir}/README.md

#
# Install PyLuwen
#	Do this as a pip install, there's not really a 'better' way
#
(
	# this is all cribbed from py3_install macro
	cd crates/pyluwen
	/usr/bin/pip install . --root %{buildroot} --prefix %{_prefix}
	rm -rfv %{buildroot}%{_bindir}/__pycache__
)

mkdir -p %{buildroot}%{cargo_registry}

%{__cp} -av crates/luwen-if %{buildroot}%{path_luwen_if}
# Modify the existing Cargo.toml to remove the path for luwen-core as we are moving it out to it's own place on the system
tomcli \
	set \
	%{buildroot}%{path_luwen_if}/Cargo.toml \
	str \
	dependencies.luwen-core \
	"$( \
		tomcli \
		get \
		%{buildroot}%{path_luwen_if}/Cargo.toml \
		dependencies.luwen-core.version \
	)"
echo "--- luwen-if Cargo.toml ---"
cat %{buildroot}%{path_luwen_if}/Cargo.toml
echo "--- /luwen-if Cargo.toml ---"
%{__cp} -av crates/luwen-ref %{buildroot}%{path_luwen_ref}
# Modify the existing Cargo.toml to remove the path for luwen-core as we are moving it out to it's own place on the system

for x in luwen-core luwen-if ttkmd-if
do
	tomcli \
		set \
		%{buildroot}%{path_luwen_ref}/Cargo.toml \
		str \
		dependencies.${x} \
		"$( \
			tomcli \
			get \
			%{buildroot}%{path_luwen_ref}/Cargo.toml \
			dependencies.${x}.version \
		)"
done

%{__cp} -av crates/ttkmd-if %{buildroot}%{path_ttkmd_if}
# Modify the existing Cargo.toml to remove the path for luwen-core as we are moving it out to it's own place on the system

# luwen-core pathfix
tomcli \
	set \
	%{buildroot}%{path_ttkmd_if}/Cargo.toml \
	str \
	dependencies.luwen-core \
	"$( \
		tomcli \
		get \
		%{buildroot}%{path_ttkmd_if}/Cargo.toml \
		dependencies.luwen-core.version \
	)"

%if %{with check}
%check
%cargo_test
%endif

%changelog
* Wed Dec 11 2024 John 'Warthog9' Hawley <jhawley@tenstorrent.com> 0.4.8-1.git.1.499b83b
- Disabling Debian 12 from the build-all (jhawley@tenstorrent.com)
- Adding PyPi workflow, this is going to be a staged commit
  (jhawley@tenstorrent.com)
- Adding Debian 12 build process (jhawley@tenstorrent.com)
- Adding 24.04 build for testing (jhawley@tenstorrent.com)
- Remove automatic only buildrelease-deb.yml (jhawley@tenstorrent.com)
- Adding git workflows to capture the full build process
  (jhawley@tenstorrent.com)
- Add debian.ubuntu (jhawley@tenstorrent.com)
- Moving debian to debian.debian (jhawley@tenstorrent.com)
- Properly return an UninitChip on 0xFFFFFFFF error (drosen@tenstorrent.com)
- Fixed bug where luwen would think dma was happening (drosen@tenstorrent.com)
- Fixed warnings created as apart of bh bringup (drosen@tenstorrent.com)
- Fixed telemetry tag parsing code (drosen@tenstorrent.com)
- Uprev versions (drosen@tenstorrent.com)
- Fixed telem tag bug (sbansal@tenstorrent.com)
- Prep for release 0.4.1 (drosen@tenstorrent.com)
- Added support for spi read/write based on fw messages
  (drosen@tenstorrent.com)
- Updated block read/write functions to work with unaligned input
  (drosen@tenstorrent.com)
- Updated read32/write32 to allow for unaligned addresses
  (drosen@tenstorrent.com)
- Fixed build error due to changing package versions (drosen@tenstorrent.com)
- Bumped minor version due to (non-breaking) blackhole changes
  (drosen@tenstorrent.com)
- Removed function implementations which are no longer needed/or out of date
  (drosen@tenstorrent.com)
- Version bumps for pyluwen, luwen-if and luwen for BH telem support
  (sbansal@tenstorrent.com)
- Added BH telemetry support (sbansal@tenstorrent.com)
- Implemented spi_read via the BH arc message queue (drosen@tenstorrent.com)
- Fixed message queues (drosen@tenstorrent.com)
- Added initial support for BH to cem (drosen@tenstorrent.com)
- Switched to using noc based axi reads/writes for BH (drosen@tenstorrent.com)
- Some read and write cleanup (drosen@tenstorrent.com)
- Added support for initial message queue interface (drosen@tenstorrent.com)
- Ported basic read/write test to BH (drosen@tenstorrent.com)
- Added initial Blackhole support to pyluwen (drosen@tenstorrent.com)
- Initial support for creating a dummy BH chip (drosen@tenstorrent.com)
- Added support for dynamically selecting spi interface
  (drosen@tenstorrent.com)
- Bumped luwen-if version to 0.4.6 (swang@tenstorrent.com)
- removed printing message (swang@tenstorrent.com)
- Bumped the version of luwen-if to 0.4.6, pyluwen to 0.5.6, luwen to 0.3.11
  (swang@tenstorrent.com)
- set threshold of arc fw version to be 1.7.0.0 (swang@tenstorrent.com)
- added bundle version in Telemetry struct (swang@tenstorrent.com)
- added fw bundle version fetching (swang@tenstorrent.com)
- Bumped pyluwen version to 0.5.5 (swang@tenstorrent.com)
- added wrapper function for eth_safe, dram_safe, and arc_alive
  (swang@tenstorrent.com)
- Bumped pyluwen and luwen-if version (swang@tenstorrent.com)
- changed the threshold to hex format (swang@tenstorrent.com)
- fetch fw bundle version (swang@tenstorrent.com)
- added explaination for DRAM, ETH, ARC, CPU initialization - Timeout or not -
  # of cores being initialized (xiaoruli@tenstorrent.com)
- added more information for chip initialization error - chip initialization
  msg - chip overall status (CPU, DRAM, ETH, ARC) - specific reason for failure
  - backtrace (xiaoruli@tenstorrent.com)
- Chore: Bumped version (drosen@tenstorrent.com)
- Fixed typo in README (drosen@tenstorrent.com)
- Fixed formatting due to pre-commit (drosen@tenstorrent.com)
- Now that things are clean, added a pre-commit hook to keep things that way
  (drosen@tenstorrent.com)
- Fixed clippy lints and compiler warnings (drosen@tenstorrent.com)
- Minor doc update to do Gitbook testing (jhawley@tenstorrent.com)
- Initial debian package testing (jhawley@tenstorrent.com)
- Adding maintainers to Cargo.toml (jhawley@tenstorrent.com)
- Automatic commit of package [rust-luwen] release [0.3.7-1].
  (jhawley@tenstorrent.com)
- Initialized to use tito. (jhawley@tenstorrent.com)

%autochangelog
* Wed Apr 03 2024 John 'Warthog9' Hawley <jhawley@tenstorrent.com> 0.3.7-1
- new package built with tito
