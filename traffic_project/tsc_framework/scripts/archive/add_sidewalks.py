import os
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="Add sidewalks and crossings to SUMO network")
    parser.add_argument("--input", default="../sumo_configs/hangzhou/hangzhou.net.xml", help="Input .net.xml file")
    parser.add_argument("--output", default="../sumo_configs/hangzhou/hangzhou_pedestrian.net.xml", help="Output .net.xml file")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)

    print(f"Adding sidewalks to {input_path}...")
    
    cmd = [
        "netconvert",
        "-s", input_path,
        "-o", output_path,
        "--sidewalks.guess", "true",
        "--crossings.guess", "true",
        "--sidewalks.guess.from-permissions", "true",
        "--tls.guess-signals", "true" # Help with crossings at TLS
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Successfully created pedestrian network: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error running netconvert: {e}")
        exit(1)
    except FileNotFoundError:
        print("Error: netconvert not found in PATH. Make sure SUMO is installed and added to PATH.")
        exit(1)

if __name__ == "__main__":
    main()
