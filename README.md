# management-gui

Manage EasyBMS installation and show live data.

## setup

install uv if missing: https://github.com/astral-sh/uv?tab=readme-ov-file#installation

### Windows

`choco install git mingw`

`uv sync`

```
cd ui
./make.bat
```

### Linux

`uv sync`

```
cd ui
make
```

## run

mqtt live:

`python mqtt_live.py`

main:

`python main.py`
