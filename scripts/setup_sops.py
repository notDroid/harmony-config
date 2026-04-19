# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml"]
# ///

import os
import subprocess
import re
import argparse
import yaml

def main():
    parser = argparse.ArgumentParser(description="Configure SOPS for environment secrets.")
    args = parser.parse_args()

    key_file = "keys.txt"
    sops_file = ".sops.yaml"

    # 1. Generate the keypair if it doesn't exist
    if not os.path.exists(key_file):
        print(f"Generating new age keypair at {key_file}...")
        try:
            subprocess.run(["age-keygen", "-o", key_file], check=True)
        except FileNotFoundError:
            print("❌ Error: 'age-keygen' is not installed or not in your PATH.")
            print("Please install it first (e.g., 'brew install age').")
            return
    else:
        print(f"🔑 {key_file} already exists. Skipping generation.")

    # 2. Extract the public key
    with open(key_file, "r") as f:
        content = f.read()
    
    match = re.search(r"# public key: (age1[a-z0-9]+)", content)
    if not match:
        print(f"❌ Error: Could not find a valid age public key in {key_file}")
        return

    pub_key = match.group(1)
    print(f"⚙️ Configuring {sops_file} with public key: {pub_key}")

    # 3. Read existing .sops.yaml or create new structure
    sops_data = {"creation_rules": []}
    if os.path.exists(sops_file):
        with open(sops_file, "r") as f:
            try:
                loaded_data = yaml.safe_load(f)
                if loaded_data and "creation_rules" in loaded_data:
                    sops_data = loaded_data
            except yaml.YAMLError:
                print(f"⚠️ Warning: {sops_file} is invalid YAML. Starting fresh.")

    # 4. Append or Overwrite rule
    target_regex = r"environments/.*/secrets\.yaml$"
    
    rule_found = False
    for rule in sops_data.get("creation_rules", []):
        if rule.get("path_regex") == target_regex:
            current_age = rule.get("age", "")
            keys = set(k.strip() for k in current_age.split(",") if k.strip())
            keys.add(pub_key)
            rule["age"] = ",".join(sorted(keys))
            rule["encrypted_regex"] = '^(secrets)$'
            rule_found = True
            print(f"🔄 Updated existing rule for {target_regex}")
            break
            
    if not rule_found:
        # Insert at the top so specific rules evaluate before any catch-all rules
        sops_data["creation_rules"].insert(0, {
            "path_regex": target_regex,
            "encrypted_regex": '^(secrets)$',
            "age": pub_key
        })
        print(f"➕ Added new exclusive rule for {target_regex}")

    # 5. Write back to .sops.yaml cleanly
    class Dumper(yaml.Dumper):
        def increase_indent(self, flow=False, *args, **kwargs):
            return super().increase_indent(flow=flow, indentless=False)

    with open(sops_file, "w") as f:
        yaml.dump(sops_data, f, Dumper=Dumper, default_flow_style=False, sort_keys=False)
    
    print("✅ SOPS configured successfully!")

if __name__ == "__main__":
    main()