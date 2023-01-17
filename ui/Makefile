all: main.py settings.py mqtt_live.py

clean:
	rm -f *.py

%.py: %.ui
	pyuic5 -x $< -o $@
