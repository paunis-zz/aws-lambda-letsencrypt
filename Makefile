.ONESHELL:

.PHONY: clean install zip

clean:
	rm -rf .venv 

install: clean
	python3 -m venv .venv
	. .venv/bin/activate
	pip3 install -r requirements.txt

zip:
	rm -f lambda_function.zip lambda_layer.zip
	pip3 install -r requirements.txt -t python/lib/python3.6/site-packages/ --system
	zip -r lambda_layer.zip python/
	zip lambda_function.zip lambda_function.py
	rm -rf python/
