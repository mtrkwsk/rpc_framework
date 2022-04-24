from inspect import signature, _empty, ismethod, isbuiltin, getmro, isfunction, getmodule
# import multiprocessing as mp
from multiprocessing import current_process
from pwt.command import command
from pwt.logs import init_logger
import pwt_config
from traceback import format_exc

logger = init_logger()

def makeRegistrar():
    registry = {}
    dispatch = {}
    def registrar(func):
        # Rejestracja funkcji tylko dla glownego procesu:
        if current_process().name == 'MainProcess':
            # return func
            if '.' in func.__qualname__:
                c_name = func.__qualname__.split('.')[0]
            else:
                c_name = 'main'
            if pwt_config.VERBOSE_REGISTER_API:
                logger.debug(f"Registering: ({func.__module__}, {c_name}) {func.__name__}{str(signature(func))}")
            if not func.__doc__:
                logger.warning(f"No docstring!!! ({func.__module__}, {c_name}) {func.__name__}{str(signature(func))}")
            for p_name, p in signature(func).parameters.items():
                if p_name != 'self' and p.annotation == _empty:
                    if p_name == 'shutdown_event':
                        continue
                    logger.warning(f"Empty parameter {p_name} annotation")
            registry[func.__name__] = func

            # if func.__name__ not in dispatch:
            dispatch[func.__name__] = c_name
            # dispatch[c_name].append(func.__name__)

        def mp(*args, **kwargs):

            # Uwaga: MainProcess.is_alive zwraca False, wiec prawidlowo wykonuje sie komenda dla PwtComponent
            # To sie moze kiedys zmienic!

            if current_process().name == 'MainProcess':
                try:
                    alive = getattr(args[0], 'is_alive')()
                    # print(f"{current_process().name} is_alive: {alive}")
                except AttributeError:
                    print ('No state [running]!')
                    return
                if alive:
                    try:
                        q = getattr(args[0], 'cmd_in_queue')
                        if not q:
                            raise AttributeError
                        cmd = command(func.__name__, **kwargs)
                        # cmd = {'cmd': func.__name__,
                        #        'args': kwargs}
                        q.put(cmd)
                        # tutaj mozna dac czekanie na nie busy
                        return
                    except AttributeError:
                        print('No queue in driver!')
                        func(*args, **kwargs)
                else:
                    # print (f"{args[0]} Driver is not alive, executing command locally.")
                    func(*args, **kwargs)
            else:
                # Tutaj ustawic ze busy
                # print('busy')
                try:
                    func(*args, **kwargs)
                except TypeError as e:
                    logger.debug(format_exc())
                    logger.error(
                        f'Command {func.__name__} has wrong arguments! {str(e)}',
                        extra={"cmd_name": func.__name__},
                    )
                # print('idle')
                # tutaj ustawic ze nie busy
        return mp
    registrar.dispatch = dispatch
    registrar.all = registry
    return registrar

api_command = makeRegistrar()


def api_info(api):
    help_dict = {}
    for f_name, f in api.all.items():
        help_dict[f_name] = {}
        help_dict[f_name]['doc'] = f.__doc__
        help_dict[f_name]['args'] = {}
        help_dict[f_name]['module'] = f.__module__
        help_dict[f_name]['return'] = None
        for arg_name, arg in f.__annotations__.items():
            if arg_name == "return":
                help_dict[f_name]['return'] = arg.__name__
                continue
            if arg_name[0] == '_':
                continue
            help_dict[f_name]['args'][arg_name] = arg.__name__ or "Any"

        if '.' in f.__qualname__:
            c_name = f.__qualname__.split('.')[0]
        else:
            c_name = 'main'
        help_dict[f_name]['class'] = c_name
        # help_dict[f_name]['multiprocess'] = (True if mp.context.Process in cls.__bases__ else None) if cls else False
    return (help_dict)
#
# def api_help():
#     help_dict = {}
#     for f_name, f in api_command.all.items():
#         help_dict[f_name] = {}
#         help_dict[f_name]['doc'] = f.__doc__
#         help_dict[f_name]['args'] = {}
#         help_dict[f_name]['module'] = f.__module__
#         help_dict[f_name]['return'] = None
#         for arg_name, arg in f.__annotations__.items():
#             if arg_name == "return":
#                 help_dict[f_name]['return'] = arg.__name__
#                 continue
#             if arg_name[0] == '_':
#                 continue
#             help_dict[f_name]['args'][arg_name] = arg.__name__
#
#         if '.' in f.__qualname__:
#             c_name = f.__qualname__.split('.')[0]
#         else:
#             c_name = 'main'
#         help_dict[f_name]['class'] = c_name
#         #help_dict[f_name]['multiprocess'] = (True if mp.context.Process in cls.__bases__ else None) if cls else False
#     print(help_dict)

# def api_call(cmd : dict):
#     if 'cmd' not in cmd:
#         print ("This is not a command!")
#         return
#     if cmd['cmd'] not in api_command.all:
#         print ("No such command!")
#         return
#     try:
#         kwargs = {}
#         if 'args' in cmd:
#             kwargs = cmd['args']
#         ret = api_command.all[cmd['cmd']](**kwargs)
#     except TypeError as e:
#         raise Exception('Command ' + str(cmd['cmd']) + ' has wrong arguments!' + str(e))
#     except Exception as e:
#         raise e
#     pass




if __name__ == '__main__':
    # @api_command
    def hello():
        print('Hello!')


    @api_command
    def hello_name(name: str):
        """Prints name"""
        print(f'Hello {name}')


    @api_command
    def add_numbers(a: int, b=3) -> int:
        """Dodaje dwa numery"""
        sum = a + b
        print(f'{a} + {b} = {sum}')
        return sum


    @api_command
    def just_return() -> str:
        return "just"


    class Klasa2:
        def __init__(self):
            pass

        @api_command
        def metoda2(self):
            print("metoda")


    # class Klasa(mp.Process):
    #     def __init__(self):
    #         pass
    #
    #     @api_command
    #     def metoda1(self):
    #         print("metoda")



    api_help()

    cmd = {
        'cmd': 'hello',
    }
    api_call(cmd)

    cmd = {
        'cmd': 'hello_name',
        'args': {'name': "elo"},
    }
    api_call(cmd)

    cmd = {
        'cmd': 'add_numbers',
        'args': {'a': 2, 'b': 10},
    }
    api_call(cmd)

# print(api_command.dispatch)