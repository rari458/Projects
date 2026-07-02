// market_data_feeder/build.rs
//
// Links the Rust feeder against the C++ engine's C ABI shared library
// (libfinancial_engine_c.so), which CMake builds into <repo>/build/src.

fn main() {
    let manifest = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let lib_dir = format!("{manifest}//../build/src");

    println!("cargo:rustc-link-search=native={lib_dir}");
    println!("cargo:rustc-link-lib=dylib=financial_engine_c");
    println!("cargo:rustc-link-lib=dylib=stdc++"); // the .so is C++; pull in libstdc++

    // Embed an rpath so the binary and tests find the .so at runtime without
    // needing LD_LIBRARY_PATH.
    println!("cargo:rustc-link-arg=-Wl,-rpath,{lib_dir}");
    
    println!("cargo:rerun-if-changed=../build/src/libfinancial_engine_c.so");
}