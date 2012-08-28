# This Makefile is intended for mingw32-make

all: crc32.exe moe-check-md5.exe itc2png.exe wavchk.exe

crc32.exe: crc32.c
	gcc -O3 crc32.c -o crc32.exe

itc2png.exe: itc2png.c
	gcc -O3 itc2png.c -o itc2png.exe

moe-check-md5.exe: moe-check-md5.c
	gcc -O3 moe-check-md5.c -o moe-check-md5.exe

wavchk.exe: wavchk.c
	gcc -O3 wavchk.c -o wavchk.exe

clean:
	rm -rf crc32.exe moe-check-md5.exe itc2png.exe wavchk.exe
