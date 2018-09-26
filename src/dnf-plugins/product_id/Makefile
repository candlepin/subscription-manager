PLUGIN=product_id.so
OBJECTS=product_id.o
CC=gcc
CPPFLAGS=`pkg-config --cflags-only-I glib-2.0 libdnf`
CFLAGS= -g -Wall -fPIC
LDFLAGS=`pkg-config --libs-only-L libdnf`
LDADD=-Wl,--as-needed -shared
LDLIBS=`pkg-config --libs-only-l glib-2.0 libdnf`

all: $(PLUGIN)

$(PLUGIN): $(OBJECTS)
	$(CC) $(LDFLAGS) $(LDADD) $< $(LDLIBS) -o $@

# The .o file is built according to the default rule and is not linked
