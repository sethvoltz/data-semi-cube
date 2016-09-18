class Utils(object):
    # Kudos http://stackoverflow.com/a/1695250/772207
    @classmethod
    def enum(*sequential, **named):
        obj = dict(zip(sequential, range(len(sequential))), **named)
        enums = obj.copy()
        reverse = dict((value, key) for key, value in obj.iteritems())
        obj.setdefault(None)
        reverse.setdefault(None)
        enums['lookup'] = obj
        enums['name'] = reverse
        return type('Enum', (), enums)

CubeMode = Utils.enum('normal', 'ambient', 'critical')
