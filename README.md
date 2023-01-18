# management-gui

Manage EasyBMS installation and show live data.

## setup

`choco install git mingw`

`pip install --prefer-binary -r requirements.txt`

```
cd ui
make
```

## run

mqtt live:

`python mqtt_live.py`

main:

`python main.py`
