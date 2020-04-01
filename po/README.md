Internationalization
--------------------

All parts of subscription-manager uses gettext to support internationalization
(subscription-manager CLI tool, cockpit plugin, yum/dnf plugins, etc.).

Translated strings for supported languages can be found in *.po files. These
files are translated by translated by translators on this address:

https://fedora.zanata.org/project/view/subscription-manager?dswid=5783

Translators needs new strings for translation in file: `po/keys.pot`. This file
can be generated using:

```bash
make gettext
```

New file `po/keys.pot` can be than uploaded to https://fedora.zanata.org.

When new strings are translated, then *.po files can be downloaded from zanata.  