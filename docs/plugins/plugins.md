# Subscription Manager Plugins

## Introduction
Subscription manager provides a simple plugin framework that allows
third-parties to modify its behavior.  The plugins are Python modules that
are loaded when subscription manager starts.

Plugins exist as a place to put functionality that is either uncommon or
not appropriate for inclusion in subscription manager's core.

## Your First Plugin
The example below shows a very basic plugin:

    #! /usr/bin/python

    from subscription_manager.base_plugin import SubManPlugin

    requires_api_version = "1.0"

    class HelloWorldPlugin(SubManPlugin):
        def post_register_consumer_hook(self, conduit):
            conduit.log.error("Hello world")

This plugin will log the phrase "Hello world" whenever subscription manager
is used to register the system.

## API Dependencies
Note the `requires_api_version` attribute in the example plugin.  This
attribute is required by subscription manager.  If your plugin does not have
it, subscription manager will refuse to load your plugin and print a message
to the log file.
 
For a plugin to be loaded, the major version required by the plugin must match
the major version in subscription manager's API version. Additionally, the 
minor version in subscription manager's API version must be greater than or 
equal the minor version required by the plugin.  If your plugin can't be loaded
because of an incompatibility with the API version, a message will be written
to the log.

This attribute is required because the information passed in through conduits
is apt to change.  If a non-backward compatible change is made, subscription
manager will increment its API version's major number and reset the minor
number to zero.  If a change is made that doesn't break backwards compatibility,
then the minor number will be incremented.

## Slots and Hooks
Plugins integrate with subscription manager by registering a "hook" function
that corresponds to a given "slot".  A slot is just a point in subscription
manager's execution.  When subscription manager reaches that point, it
executes all of the hook functions associate with that slot.

Registering your hook functions is easy.  The plugin class is inspected for
functions names of the form *slotname*\_hook.  If a function matching a valid
slot is found, it is automatically registered.

The following slots exist:

> pre\_product\_id\_install
>
> post\_product\_id\_install
>
> pre\_register\_consumer
>
> post\_register\_consumer
>
> post\_facts\_collection
>
> pre\_subscribe
>
> post\_subscribe

## Conduits
All hooks are passed a single argument: a conduit.  A conduit provides methods
and attributes that can be used by the plugin.

The conduit varies depending on the plugin slot.  Consult the source to
determine which conduit is available for a given slot.  All conduits are
subclassed from the `BaseConduit` class and have, at a minimum, handles
to the subscription manager log and to the plugin configuration.


## How a plugin is invoked
Before plugin slots are reached, subscription-manager instantiates
a `plugins.PluginManager` object. It will search plugin configuration
and find and load enabled plugin modules and classes. It also maps
plugin  hooks to PluginManager slots.

In subscription-manager code, a "slot" is invoked by calling

    PluginManager().run('a\_plugin\_slot\_name',
                        plugin\_arg,
                        other\_plugin\_arg)

PluginManager() looks up the slot name, and finds all the plugin
hooks mapped to it. It also finds the corresponding Conduit()
class.

run() then iterates over the set of plugin hook methods. For
each method, it creates a new Conduit() class, passing it's constructor
any of the method args passed to run(). Note the args to run() are
passed to the Conduit.\_\_init\_\_, not to the plugin method hook directly.

The new Conduit() is passed to the plugin's hook method. Nothing
is returned from pluginManager.run(). Objects passed to
PluginManager.run() are passed by reference, so a plugin can
modify them. If you need to return data from a plugin, the
plugin Conduit() needs to know to add it to the conduit object
passed to the plugin method. Only the Conduit() is passed to
the plugin method, so anything that needs to be passed needs
to be added to the Conduit object.

## Plugin Configuration
Every plugin has its own configuration file located in 
`/etc/rhsm/pluginconf.d`.  These configuration files follow the standard INI
file conventions used by subscription manager's own configuration file.  The
configuration file for a plugin should follow the convention 
`module_name`.`class_name`.conf.  For example, if our Hello World plugin
seen above were in a file named `hello.py`, the configuration file should be
named `hello.HelloWorldPlugin.conf`.

Items can be read from the configuration via methods available on the conduit.

    def confString(self, section, option, default=None)

    def confBool(self, section, option, default=None)

    def confInt(self, section, option, default=None)

    def confFloat(self, section, option, default=None)

If the option is missing from the configuration file, then the default value
passed in to the method will be returned.

Every plugin should have at least the following in its configuration file.

    [main]
    enabled = 1

The plugin framework looks for the `enabled` option in the `main` section when
determining whether or not to load a plugin.

## Examples
The best way to learn more about plugins is by looking at some examples.
Subscription manager has several plugins available in the
example-plugins/ directory._
