import pandas as pd
import os

dir1 = "new_dir"
dir2 = "og_dir"
output_path = "duplicates.csv"
hashes = dict()
duplicates = pd.DataFrame(columns=["hash", "path"])

# Build a dictionary of the hashes from the original directory
for _file in os.scandir(dir1):
    hashes[_file.name] = False
# Look for duplicates in new directory
for _file in os.scandir(dir2):
    try:
        nothing = hashes[_file.name]
        # If we made it here then we have a duplicate
        dupe = pd.Series({"hash": _file.name, "path": _file.path})
        duplicates = duplicates.append(dupe, ignore_index=True)
    except KeyError:
        # If we made it here then this file's hash wasn't in the original directory
        pass

duplicates.to_csv(output_path)

