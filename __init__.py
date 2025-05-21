def classFactory(iface):
    from .querybuilder import QueryBuilder
    return QueryBuilder(iface)
