clean: clean_log clean_pyc

clean_all: clean_log clean_cfg clean_pyc

clean_log:
	cd logs;rm -rf *

clean_cfg:
	find . -name '*.cfg' -exec rm -rf {} \;

clean_pyc:
	find . -name '*.pyc' -exec rm -rf {} \;
