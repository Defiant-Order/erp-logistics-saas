import contextvars

_current_tenant_id = contextvars.ContextVar("current_tenant_id", default=None)


def get_current_tenant_id():
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id):
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token):
    _current_tenant_id.reset(token)


class tenant_context:
    """Context manager que escopea las queries de TenantManager a un tenant dentro del bloque `with`.

    El middleware de request (a implementarse junto con la capa HTTP) usará el mismo
    mecanismo para setear el tenant en contexto a partir del usuario autenticado.
    """

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self._token = None

    def __enter__(self):
        self._token = set_current_tenant_id(self.tenant_id)
        return self

    def __exit__(self, *exc_info):
        reset_current_tenant_id(self._token)
