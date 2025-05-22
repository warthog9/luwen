use std::{env, fs};

fn compiled_proto_file_by_name(
    name: &str,
    out_dir: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let proto_file = format!("{}.proto", name);
    let outname = format!("{}/{}.rs", out_dir, name);
    let mut protoc_build_config = prost_build::Config::new();
    protoc_build_config.out_dir(out_dir);

    // Add `#[derive(Serialize)]` to all generated messages for easy HashMap conversion
    protoc_build_config.type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]");

    protoc_build_config.compile_protos(&[proto_file], &["bh_spirom_protobufs/"])?;
    fs::rename(format!("{}/_.rs", out_dir), outname)?;

    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the output directory from Cargo
    let out_dir = env::var("OUT_DIR")?;
    compiled_proto_file_by_name("fw_table", &out_dir)?;
    compiled_proto_file_by_name("flash_info", &out_dir)?;
    compiled_proto_file_by_name("read_only", &out_dir)?;

    Ok(())
}
