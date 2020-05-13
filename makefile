all: reset install_pyggi install_code install_data

reset:
	mkdir -p archives
	rm -rf artefact/pyggi
	rm -rf artefact/code
	mkdir -p artefact/code
	rm -rf artefact/data
	mkdir -p artefact/data

install_code: install_minisat install_optipng install_moead

install_data: install_data_satcit install_data_satuniform install_data_png

archives/pyggi_6cb31a3.tar.gz:
	git clone https://github.com/coinse/pyggi.git
	cd pyggi && git checkout 6cb31a3
	rm -rf pyggi/.git
	tar czf $@ pyggi
	rm -rf pyggi

archives/minisat-2.2.0.tar.gz:
	wget 'http://minisat.se/downloads/minisat-2.2.0.tar.gz' -O $@

archives/minisat-2.2.0.tar.gz_backup:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/minisat-2.2.0.tar.gz' -O $@

archives/sat4j_016981c0.tar.gz:
	git clone https://gitlab.ow2.org/sat4j/sat4j.git
	cd sat4j && git checkout 016981c0
	rm -rf sat4j/.git
	tar czf $@ sat4j
	rm -rf sat4j

archives/sat4j_016981c0.tar.gz_backup:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/sat4j_2.3.6_016981c0.tar.gz' -O $@

archives/optipng-0.7.7.tar.gz:
	wget 'https://sourceforge.net/projects/optipng/files/OptiPNG/optipng-0.7.7/optipng-0.7.7.tar.gz/download' -O $@

archives/optipng-0.7.7.tar.gz_backup:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/optipng-0.7.7.tar.gz' -O $@

archives/MOEA-D-DE.rar:
	wget 'https://web.archive.org/web/20170422063433/http://dces.essex.ac.uk/staff/qzhang/code/MOEADDE/MOEA-D-DE.rar' -O $@

archives/MOEA-D-DE.rar_backup:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/MOEA-D-DE.rar' -O $@

archives/sat_cit2.tar.gz:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/tevc2020_sat_cit2.tar.gz' -O $@

archives/sat_uniform.tar.gz:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/tevc2020_sat_uniform.tar.gz' -O $@

archives/png_color.tar.gz:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/tevc2020_png_color.tar.gz' -O $@

archives/png_greyscale.tar.gz:
	wget 'http://www0.cs.ucl.ac.uk/staff/a.blot/files/tevc2020_png_greyscale.tar.gz' -O $@

install_pyggi: archives/pyggi_6cb31a3.tar.gz
	rm -rf artefact/pyggi
	tar -C artefact -xf $<
	patch -d artefact -p 1 < instr/pyggi.patch
	mv artefact/pyggi foo
	mv foo/pyggi artefact
	rm -r foo

install_minisat: archives/minisat-2.2.0.tar.gz
	rm -rf artefact/code/minisat-2.2.0
	tar -C artefact/code -xf $<
	mv artefact/code/minisat artefact/code/minisat-2.2.0
	patch -d artefact/code -p 1 < instr/minisat.patch
	cd artefact/code/minisat-2.2.0/simp && MROOT=.. CFLAGS='-fpermissive' make minisat
	cp instr/Solver.cc.xml artefact/code/minisat-2.2.0/core

install_sat4j: archives/sat4j_016981c0.tar.gz
	rm -rf artefact/code/sat4j
	tar -C artefact/code -xf $<
	patch -d artefact/code -p 1 < instr/sat4j.patch
	rm -r artefact/code/sat4j/org.sat4j.pb
	cd artefact/code/sat4j && ant core
	cp instr/Solver.java.xml artefact/code/sat4j/org.sat4j.core/src/main/java/org/sat4j/minisat/core

install_optipng: archives/optipng-0.7.7.tar.gz
	rm -rf artefact/code/optipng-0.7.7
	tar -C artefact/code -xf $<
	cd artefact/code/optipng-0.7.7 && ./configure
	cd artefact/code/optipng-0.7.7/src/optipng && make
	cp instr/{optim,optipng}.c.xml artefact/code/optipng-0.7.7/src/optipng

install_moead: archives/MOEA-D-DE.rar
	rm -rf artefact/code/moead-2007
	unrar x $< artefact/code/moead-2007/
	mkdir artefact/code/moead-2007/{GD,POF,POS}
	patch -d artefact/code -p 1 < instr/moead.patch
	cd artefact/code/moead-2007 && make main_moea
	cp instr/recombination.h.xml artefact/code/moead-2007/common
	cp instr/dmoeafunc.h.xml artefact/code/moead-2007/DMOEA
	cp instr/nsga2func.h.xml artefact/code/moead-2007/NSGA2

install_data_satcit: archives/sat_cit2.tar.gz
	tar -C artefact/data -xf $<

install_data_satuniform: archives/sat_uniform.tar.gz
	tar -C artefact/data -xf $<

install_data_png: archives/png_color.tar.gz archives/png_greyscale.tar.gz
	tar -C artefact/data -xf archives/png_color.tar.gz
	tar -C artefact/data -xf archives/png_greyscale.tar.gz
