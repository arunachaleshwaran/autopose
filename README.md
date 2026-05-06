# Getting Started

## Environment Setup
```sh
# Clone the repository
git clone https://github.com/arunachaleshwaran/autopose.git
# Navigate to the project directory
cd autopose
# Install dependencies
conda create -n autopose python=3.12 -y
conda activate autopose
```

updating environment.yml
```sh
conda env update -f environment.yml --prune
```

## For Blender scripting (optional)
Adds `bpy` type stubs so your IDE autocompletes Blender's Python API. Stubs only — does not install Blender or let you `import bpy` at runtime. Scripts still run via `blender --background --python script.py`.

```sh
conda env update --name autopose -f environment-blender.yml
```

# Data Set Creation
```sh
/Applications/Blender.app/Contents/MacOS/Blender --background \
     --python ./script/blender/ico-sphere-template-162.py
```