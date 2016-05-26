def import_class(name):
    """Load a class from a string.  Thanks http://stackoverflow.com/a/547867/6124862"""
    components = name.split('.')
    module = __import__(components[0])
    for comp in components[1:]:
        module = getattr(module, comp)
    return module
