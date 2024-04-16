all: main.py settings.py mqtt_live.py

clean:
	rm -f *.py

%.py: %.ui
	pyuic6 -x $< -o $@
