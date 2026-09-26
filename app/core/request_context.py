from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
current_user_id_ctx: ContextVar[str] = ContextVar[str]("current_user_id", default="-")
