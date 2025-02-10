def docullim(arg: str | None = None):
    """
    Decorator for marking functions or classes for automatic documentation generation.

    Usage:
      @docullim
      def foo():
          pass

      or

      @docullim("my_tag")
      def foo():
          pass
    """
    if callable(arg):
        # Used as @docullim without arguments.
        func = arg
        setattr(func, "_auto_doc", True)
        setattr(func, "_auto_doc_tag", None)
        return func
    else:
        # Used as @docullim("tag")
        tag = arg

        def decorator(func):
            setattr(func, "_auto_doc", True)
            setattr(func, "_auto_doc_tag", tag)
            return func

        return decorator
