all: main.py settings.py mqtt_live.py

clean:
	rm -f *.py

%.py: %.ui
	../venv/Scripts/pyuic6 -x $< -o $@
