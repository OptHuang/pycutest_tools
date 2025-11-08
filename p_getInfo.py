import io
import re
import os
import sys
import numpy as np
import pandas as pd
from concurrent.futures import TimeoutError
import threading
import gc

from multiprocessing import Process, Queue
import signal


# Add optiprofiler to the system path
import os
import sys
cwd = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cwd, 'optiprofiler'))
sys.path.append(os.path.join(cwd, 'optiprofiler', 'problems'))
from problems.pycutest.pycutest_tools import pycutest_load, pycutest_select, pycutest_get_sif_params, pycutest_clear_cache

# Define the problem block number
num_blocks = 20
current_block = 19

# Set the timeout (seconds) for each problem to be loaded
timeout = 30

# Collect the names of the problems
problem_names = pycutest_select({})
# problem_names = ['CHENHARK']

# Timeout or memory blacklist
timeout_memory_blacklist = ['BA-L52', 'BA-L16', 'BA-L16LS', 'BA-L52LS', 'BDRY2', 'NET4', 'PDE1', 'PDE2']

# Exclude some problems
problem_exclude = []
problem_names = [name for name in problem_names if name not in problem_exclude and name not in timeout_memory_blacklist]
problem_names.sort()

# Choose the problems in the current block
total_problems = len(problem_names)
block_size = (total_problems + num_blocks - 1) // num_blocks
start_idx = current_block * block_size
end_idx = min(start_idx + block_size, total_problems)
problem_names = problem_names[start_idx:end_idx]

# List all known feasibility problems
known_feasibility = [
    'AIRCRFTA', 'ARGAUSS', 'ARGLALE', 'ARGLBLE', 'ARGTRIG', 'ARTIF', 'BAmL1SP', 'BARDNE', 'BEALENE', 'BENNETT5', 'BIGGS6NE', 'BOOTH', 'BOXBOD', 'BRATU2D', 'BRATU2DT', 'BRATU3D', 'BROWNBSNE', 'BROWNDENE', 'BROYDN3D', 'CBRATU2D', 'CBRATU3D', 'CHANDHEQ', 'CHEMRCTA', 'CHWIRUT2', 'CLUSTER', 'COOLHANS', 'CUBENE', 'CYCLIC3', 'CYCLOOCF', 'CYCLOOCT', 'DANIWOOD', 'DANWOOD', 'DECONVBNE', 'DENSCHNBNE', 'DENSCHNDNE', 'DENSCHNFNE', 'DEVGLA1NE', 'DEVGLA2NE', 'DRCAVTY1', 'DRCAVTY2', 'DRCAVTY3', 'ECKERLE4', 'EGGCRATENE', 'EIGENA', 'EIGENB', 'ELATVIDUNE', 'ENGVAL2NE', 'ENSO', 'ERRINROSNE', 'ERRINRSMNE', 'EXP2NE', 'EXTROSNBNE', 'FLOSP2HH', 'FLOSP2HL', 'FLOSP2HM', 'FLOSP2TH', 'FLOSP2TL', 'FLOSP2TM', 'FREURONE', 'GENROSEBNE', 'GOTTFR', 'GROWTH', 'GULFNE', 'HAHN1', 'HATFLDANE', 'HATFLDBNE', 'HATFLDCNE', 'HATFLDDNE', 'HATFLDENE', 'HATFLDFLNE', 'HATFLDF', 'HATFLDG', 'HELIXNE', 'HIMMELBA', 'HIMMELBC', 'HIMMELBD', 'HIMMELBFNE', 'HS1NE', 'HS25NE', 'HS2NE', 'HS8', 'HYDCAR20', 'HYDCAR6', 'HYPCIR', 'INTEGREQ', 'INTEQNE', 'KOEBHELBNE', 'KOWOSBNE', 'KSS', 'LANCZOS1', 'LANCZOS2', 'LANCZOS3', 'LEVYMONE10', 'LEVYMONE5', 'LEVYMONE6', 'LEVYMONE7', 'LEVYMONE8', 'LEVYMONE9', 'LEVYMONE', 'LIARWHDNE', 'LINVERSENE', 'LSC1', 'LSC2', 'LUKSAN11', 'LUKSAN12', 'LUKSAN13', 'LUKSAN14', 'LUKSAN17', 'LUKSAN21', 'LUKSAN22', 'MANCINONE', 'METHANB8', 'METHANL8', 'MEYER3NE', 'MGH09', 'MGH10', 'MISRA1A', 'MISRA1B', 'MISRA1C', 'MISRA1D', 'MODBEALENE', 'MSQRTA', 'MSQRTB', 'MUONSINE', 'n10FOLDTR', 'NELSON', 'NONSCOMPNE', 'NYSTROM5', 'OSBORNE1', 'OSBORNE2', 'OSCIGRNE', 'OSCIPANE', 'PALMER1ANE', 'PALMER1BNE', 'PALMER1ENE', 'PALMER1NE', 'PALMER2ANE', 'PALMER2BNE', 'PALMER2ENE', 'PALMER3ANE', 'PALMER3BNE', 'PALMER3ENE', 'PALMER4ANE', 'PALMER4BNE', 'PALMER4ENE', 'PALMER5ANE', 'PALMER5BNE', 'PALMER5ENE', 'PALMER6ANE', 'PALMER6ENE', 'PALMER7ANE', 'PALMER7ENE', 'PALMER8ANE', 'PALMER8ENE', 'PENLT1NE', 'PENLT2NE', 'POROUS1', 'POROUS2', 'POWELLBS', 'POWELLSQ', 'POWERSUMNE', 'PRICE3NE', 'PRICE4NE', 'QINGNE', 'QR3D', 'RAT42', 'RAT43', 'RECIPE', 'REPEAT', 'RES', 'ROSZMAN1', 'RSNBRNE', 'SANTA', 'SEMICN2U', 'SEMICON1', 'SEMICON2', 'SPECANNE', 'SSBRYBNDNE', 'SSINE', 'THURBER', 'TQUARTICNE', 'VANDERM1', 'VANDERM2', 'VANDERM3', 'VANDERM4', 'VARDIMNE', 'VESUVIA', 'VESUVIO', 'VESUVIOU', 'VIBRBEAMNE', 'WATSONNE', 'WAYSEA1NE', 'WAYSEA2NE', 'YATP1CNE', 'YATP2CNE', 'YFITNE', 'ZANGWIL3'
]

# To store all the feasibility problems including the known ones and the new ones
feasibility = []

# To store all the 'time out' problems
timeout_problems = []

saving_path = cwd

# Define the class logger
class Logger(object):
    def __init__(self, logfile):
        self.terminal = sys.__stdout__
        self.log = logfile
    def write(self, message):
        self.terminal.write(message)
        try:
            self.log.write(message)
        except Exception as e:
            self.terminal.write(f"[Logger Error] {e}\n")
    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Record the log from terminal
log_file = open(os.path.join(saving_path, 'log_pycutest.txt'), 'w')
sys.stdout = Logger(log_file)
sys.stderr = Logger(log_file)

# def run_with_timeout(func, args, timeout_seconds):
#     def handler(signum, frame):
#         raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")

#     signal.signal(signal.SIGALRM, handler)
#     signal.alarm(timeout_seconds)
    
#     try:
#         result = func(*args) if args else func()
#         return result
#     finally:
#         signal.alarm(0)

# def run_with_timeout(func, args, timeout_seconds):
#     """使用独立进程，超时可完全终止"""
#     queue = Queue()
    
#     def wrapper():
#         # ✅ 子进程中忽略信号，防止干扰
#         signal.signal(signal.SIGINT, signal.SIG_IGN)
        
#         try:
#             result = func(*args) if args else func()
#             queue.put(('success', result))
#         except Exception as e:
#             queue.put(('error', str(e)))
    
#     process = Process(target=wrapper)
#     process.start()
#     process.join(timeout=timeout_seconds)
    
#     if process.is_alive():
#         # ✅ 强制终止，所有资源自动释放
#         process.terminate()
#         process.join(timeout=1)
        
#         if process.is_alive():
#             process.kill()
        
#         raise TimeoutError(f"Timeout after {timeout_seconds}s")
    
#     if not queue.empty():
#         status, data = queue.get()
#         if status == 'error':
#             raise RuntimeError(data)
#         return data
    
#     raise RuntimeError("Process failed without result")

# def run_with_timeout(func, args, timeout_seconds):
#     result = [None]
#     exception = [None]
    
#     def wrapper():
#         try:
#             result[0] = func(*args) if args else func()
#         except Exception as e:
#             exception[0] = e
    
#     thread = threading.Thread(target=wrapper, daemon=True)
#     thread.start()
#     thread.join(timeout=timeout_seconds)
    
#     if thread.is_alive():
#         raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")
    
#     if exception[0] is not None:
#         raise exception[0]
    
#     return result[0]

def run_with_timeout(func, args, timeout_seconds):
    result = [None]
    exception = [None]
    
    def wrapper():
        try:
            result[0] = func(*args) if args else func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        print(f"Function with args {args} timed out after {timeout_seconds} seconds, but continuing execution.")
    
    thread.join()
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]


# Define a function to get information about a problem
def get_problem_info(problem_name, known_feasibility, para_names=None, para_values=None, para_defaults=None):

    print(f"Processing problem: {problem_name}")

    info_single = {
        'problem_name': problem_name,
        'ptype': 'unknown',
        'xtype': 'unknown',
        'dim': 'unknown',
        'mb': 'unknown',
        'ml': 'unknown',
        'mu': 'unknown',
        'mcon': 'unknown',
        'mlcon': 'unknown',
        'mnlcon': 'unknown',
        'm_ub': 'unknown',
        'm_eq': 'unknown',
        'm_linear_ub': 'unknown',
        'm_linear_eq': 'unknown',
        'm_nonlinear_ub': 'unknown',
        'm_nonlinear_eq': 'unknown',
        'f0': 0,
        'isfeasibility': 1,
        'isgrad': 0,
        'ishess': 0,
        'isjcub': 0,
        'isjceq': 0,
        'ishcub': 0,
        'ishceq': 0,
        'argins': '',
        'dims': '',
        'mbs': '',
        'mls': '',
        'mus': '',
        'mcons': '',
        'mlcons': '',
        'mnlcons': '',
        'm_ubs': '',
        'm_eqs': '',
        'm_linear_ubs': '',
        'm_linear_eqs': '',
        'm_nonlinear_ubs': '',
        'm_nonlinear_eqs': '',
        'f0s': ''}
    try:
        p = run_with_timeout(pycutest_load, (problem_name,), timeout)
        # p = pycutest_load(problem_name)
    except TimeoutError:
        print(f"Timeout while loading problem {problem_name}.")
        timeout_problems.append(problem_name)
        print(f"Skipping problem {problem_name} due to timeout.")
        return info_single

    try:
        info_single['ptype'] = p.ptype
        info_single['xtype'] = 'r'
        info_single['dim'] = p.n
        info_single['mb'] = p.mb
        info_single['ml'] = sum(p.xl > -np.inf)
        info_single['mu'] = sum(p.xu < np.inf)
        info_single['mcon'] = p.mcon
        info_single['mlcon'] = p.mlcon
        info_single['mnlcon'] = p.mnlcon
        info_single['m_ub'] = p.m_linear_ub + p.m_nonlinear_ub
        info_single['m_eq'] = p.m_linear_eq + p.m_nonlinear_eq
        info_single['m_linear_ub'] = p.m_linear_ub
        info_single['m_linear_eq'] = p.m_linear_eq
        info_single['m_nonlinear_ub'] = p.m_nonlinear_ub
        info_single['m_nonlinear_eq'] = p.m_nonlinear_eq
    except Exception as e:
        print(f"Error while getting problem info for {problem_name}: {e}")

    try:
        # f = run_with_timeout(p.fun, (p.x0,), timeout)
        f = p.fun(p.x0)
        if problem_name == 'LIN':
            info_single['isfeasibility'] = 0
        elif np.size(f) == 0 or np.isnan(f) or problem_name in known_feasibility:
            info_single['isfeasibility'] = 1
            feasibility.append(problem_name)
        else:
            info_single['isfeasibility'] = 0
        if problem_name == 'LIN':
            info_single['f0'] = np.nan
        elif np.size(f) == 0 or np.isnan(f) or (problem_name in known_feasibility and problem_name != 'HS8'):
            info_single['f0'] = 0
        else:
            info_single['f0'] = f
    except Exception as e:
        print(f"Error while evaluating function for {problem_name}: {e}")
        info_single['f0'] = 0
        info_single['isfeasibility'] = 1
        feasibility.append(problem_name)
    
    if problem_name in feasibility:
        info_single['isgrad'] = 1
        info_single['ishess'] = 1
    else:
        info_single['isgrad'] = 1
        info_single['ishess'] = 1
        # try:
        #     g = run_with_timeout(p.grad, (p.x0,), timeout)
        #     # g = p.grad(p.x0)
        #     if g.size == 0:
        #         info_single['isgrad'] = 0
        #     else:
        #         info_single['isgrad'] = 1
        # except Exception as e:
        #     print(f"Error while evaluating gradient for {problem_name}: {e}")
        #     info_single['isgrad'] = 0
        # try:
        #     h = run_with_timeout(p.hess, (p.x0,), timeout)
        #     # h = p.hess(p.x0)
        #     if h.size == 0:
        #         info_single['ishess'] = 0
        #     else:
        #         info_single['ishess'] = 1
        # except Exception as e:
        #     print(f"Error while evaluating hessian for {problem_name}: {e}")
        #     info_single['ishess'] = 0
    
    info_single['isjcub'] = 1
    # try:
    #     jc = run_with_timeout(p.jcub, (p.x0,), timeout)
    #     # jc = p.jcub(p.x0)
    #     if jc.size == 0:
    #         info_single['isjcub'] = 0
    #     else:
    #         info_single['isjcub'] = 1
    # except Exception as e:
    #     print(f"Error while evaluating jcub for {problem_name}: {e}")
    #     info_single['isjcub'] = 0
    
    info_single['isjceq'] = 1
    # try:
    #     jc = run_with_timeout(p.jceq, (p.x0,), timeout)
    #     # jc = p.jceq(p.x0)
    #     if jc.size == 0:
    #         info_single['isjceq'] = 0
    #     else:
    #         info_single['isjceq'] = 1
    # except Exception as e:
    #     print(f"Error while evaluating jceq for {problem_name}: {e}")
    #     info_single['isjceq'] = 0
    
    info_single['ishcub'] = 1
    # try:
    #     hc = run_with_timeout(p.hcub, (p.x0,), timeout)
    #     # hc = p.hcub(p.x0)
    #     if len(hc) == 0:
    #         info_single['ishcub'] = 0
    #     else:
    #         info_single['ishcub'] = 1
    # except Exception as e:
    #     print(f"Error while evaluating hcub for {problem_name}: {e}")
    #     info_single['ishcub'] = 0
    
    info_single['ishceq'] = 1
    # try:
    #     hc = run_with_timeout(p.hceq, (p.x0,), timeout)
    #     # hc = p.hceq(p.x0)
    #     if len(hc) == 0:
    #         info_single['ishceq'] = 0
    #     else:
    #         info_single['ishceq'] = 1
    # except Exception as e:
    #     print(f"Error while evaluating hceq for {problem_name}: {e}")
    #     info_single['ishceq'] = 0

    # Clear the cached problem to save memory and the variable 'p'
    pycutest_clear_cache(problem_name)
    if 'p' in locals() and p is not None:
        try:
            del p
        except:
            pass
    gc.collect()

    if para_names is None or len(para_names) == 0:
        print(f"Finished processing problem {problem_name} without parameters.")
        return info_single

    # Collect additional information if the problem is parametric
    print(f"Processing parametric problem: {problem_name} with parameters: {para_names}, values: {para_values}, defaults: {para_defaults}")

    # Define a sub-function to process each argument (so that later we can use the ``run_with_timeout`` function)
    def process_arg(problem_name, para_dict):
        try:
            p = pycutest_load(problem_name, **para_dict)

            result = {}
            result['n'] = p.n
            result['mb'] = p.mb
            result['ml'] = sum(p.xl > -np.inf)
            result['mu'] = sum(p.xu < np.inf)

            try:
                result['mcon'] = p.mcon
            except AttributeError as e:
                if "'Problem' object has no attribute '_m_nonlinear_ub'" in str(e):
                    result['mcon'] = p.mlcon + p.m_nonlinear_ub + p.m_nonlinear_eq
                else:
                    raise e
            
            result['mlcon'] = p.mlcon
            
            try:
                result['mnlcon'] = p.mnlcon
            except AttributeError as e:
                if "'Problem' object has no attribute '_m_nonlinear" in str(e):
                    result['mnlcon'] = p.m_nonlinear_ub + p.m_nonlinear_eq
                else:
                    raise e
            
            result['m_ub'] = p.m_linear_ub + p.m_nonlinear_ub
            result['m_eq'] = p.m_linear_eq + p.m_nonlinear_eq
            result['m_linear_ub'] = p.m_linear_ub
            result['m_linear_eq'] = p.m_linear_eq
            result['m_nonlinear_ub'] = p.m_nonlinear_ub
            result['m_nonlinear_eq'] = p.m_nonlinear_eq
            
            if problem_name in known_feasibility:
                result['f0'] = 0
            else:
                f = p.fun(p.x0)
                if np.size(f) == 0 or np.isnan(f):
                    result['f0'] = 0
                else:
                    result['f0'] = f
                    
            return True, result
        except Exception as e:
            print(f"Error processing problem {problem_name} with parameters {para_dict}: {e}")
            return False, para_dict, None


    para_combinations = np.array(np.meshgrid(*para_values)).T.reshape(-1, len(para_names))
    nondefault_para_combinations = []
    if para_defaults is not None and all(d is not None for d in para_defaults):
        for comb in para_combinations:
            if not all(comb[i] == para_defaults[i] for i in range(len(para_names))):
                nondefault_para_combinations.append(comb)
    else:
        nondefault_para_combinations = para_combinations
    successful_para_combinations = []


    for comb in nondefault_para_combinations:
        print(f"Processing problem {problem_name} with parameter combination: {comb}")
        try:
            # If the parameter is too big (greater than 1e5), skip it directly to avoid long time consumption
            # Note: `comb` elements often are numpy scalar types (e.g. np.int64), which are not instances
            # of Python's built-in int/float. Use np.isscalar (or numbers.Number) so numpy scalars are
            # correctly detected and large values are skipped.
            skip_combination = False
            for val in comb:
                try:
                    if np.isscalar(val) and abs(val) >= 1e5:
                        print(f"Skipping parameter combination {comb} due to large value: {val}")
                        skip_combination = True
                        break
                except Exception:
                    # If comparison fails (non-numeric), just ignore this value
                    continue
            if skip_combination:
                continue

            # Skip some specific combinations if needed
            if problem_name == 'ALLINQP':
                if comb[0] >= 100000:
                    print(f"Skipping parameter combination {comb} for problem ALLINQP due to known issues.")
                    continue
            if problem_name == 'AUG2D':
                if comb[0] >= 200 and comb[1] >= 200:
                    print(f"Skipping parameter combination {comb} for problem AUG2D due to known issues.")
                    continue
            if problem_name == 'AUG2DC':
                if comb[0] >= 200 and comb[1] >= 200:
                    print(f"Skipping parameter combination {comb} for problem AUG2DC due to known issues.")
                    continue
            if problem_name == 'AUG2DCQP':
                if comb[0] >= 200 and comb[1] >= 200:
                    print(f"Skipping parameter combination {comb} for problem AUG2DCQP due to known issues.")
                    continue
            if problem_name == 'AUG2DQP':
                if comb[0] >= 200 and comb[1] >= 200:
                    print(f"Skipping parameter combination {comb} for problem AUG2DQP due to known issues.")
                    continue
            if problem_name == 'AUG3DC':
                if comb[0] >= 30 and comb[1] >= 20 and comb[2] >= 30:
                    print(f"Skipping parameter combination {comb} for problem AUG3DC due to known issues.")
                    continue
            if problem_name == 'AUG3DQP':
                if comb[0] >= 30 and comb[1] >= 20 and comb[2] >= 30:
                    print(f"Skipping parameter combination {comb} for problem AUG3DQP due to known issues.")
                    continue
            if problem_name == 'AUG3DCQP':
                if comb[0] >= 20 and comb[1] >= 20 and comb[2] >= 20:
                    print(f"Skipping parameter combination {comb} for problem AUG3DCQP due to known issues.")
                    continue
            if problem_name == 'BLOCKQP4':
                if comb[0] >= 10000:
                    print(f"Skipping parameter combination {comb} for problem BLOCKQP4 due to known issues.")
                    continue
            if problem_name == 'BLOCKQP5':
                if comb[0] >= 10000:
                    print(f"Skipping parameter combination {comb} for problem BLOCKQP5 due to known issues.")
                    continue
            if problem_name == 'BDVALUES':
                if comb[0] >= 1e4 and comb[1] >= 100:
                    print(f"Skipping parameter combination {comb} for problem BDVALUES due to known issues.")
                    continue
            if problem_name == 'CHARDIS0':
                if comb[0] >= 2000:
                    print(f"Skipping parameter combination {comb} for problem CHARDIS0 due to known issues.")
                    continue
            if problem_name == 'CHARDIS1':
                if comb[0] >= 2000:
                    print(f"Skipping parameter combination {comb} for problem CHARDIS1 due to known issues.")
                    continue
            if problem_name == 'CONT5-QP':
                if comb[0] >= 400:
                    print(f"Skipping parameter combination {comb} for problem CONT5-QP due to known issues.")
                    continue
            if problem_name == 'CONT6-QQ':
                if comb[0] >= 400:
                    print(f"Skipping parameter combination {comb} for problem CONT6-QQ due to known issues.")
                    continue
            if problem_name == 'DTOC1NC':
                if comb[0] >= 1000 and comb[1] >= 5 and comb[2] >= 10:
                    print(f"Skipping parameter combination {comb} for problem DTOC1NC due to known issues.")
                    continue
            if problem_name == 'GAUSSELM':
                if comb[0] >=50:
                    print(f"Skipping parameter combination {comb} for problem GAUSSELM due to known issues.")
                    continue
            if problem_name == 'HARKERP2':
                if comb[0] >= 5000:
                    print(f"Skipping parameter combination {comb} for problem HARKERP2 due to known issues.")
                    continue
            if problem_name == 'JUNKTURN':
                if comb[0] >= 100000:
                    print(f"Skipping parameter combination {comb} for problem JUNKTURN due to known issues.")
                    continue
            if problem_name == 'LUKVLE13':
                if comb[0] >= 99998:
                    print(f"Skipping parameter combination {comb} for problem LUKVLE13 due to known issues.")
                    continue
            if problem_name == 'LUKVLI14':
                if comb[0] >= 99998:
                    print(f"Skipping parameter combination {comb} for problem LUKVLI14 due to known issues.")
                    continue
            if problem_name == 'LUKVLI15':
                if comb[0] >= 99997:
                    print(f"Skipping parameter combination {comb} for problem LUKVLI15 due to known issues.")
                    continue
            if problem_name == 'LUKVLI16':
                if comb[0] >= 99997:
                    print(f"Skipping parameter combination {comb} for problem LUKVLI16 due to known issues.")
                    continue
            if problem_name == 'LUKVLI17':
                if comb[0] >= 99997:
                    print(f"Skipping parameter combination {comb} for problem LUKVLI17 due to known issues.")
                    continue
            if problem_name == 'NUFFIELD':
                if comb[0] >= 100:
                    print(f"Skipping parameter combination {comb} for problem NUFFIELD due to known issues.")
                    continue
            if problem_name == 'OPTCTRL6':
                if comb[0] >= 50000:
                    print(f"Skipping parameter combination {comb} for problem OPTCTRL6 due to known issues.")
                    continue
            if problem_name == 'ORTHREGA':
                if comb[0] >= 8:
                    print(f"Skipping parameter combination {comb} for problem ORTHREGA due to known issues.")
                    continue
            if problem_name == 'ORTHREGC':
                if comb[0] >= 50000:
                    print(f"Skipping parameter combination {comb} for problem ORTHREGC due to known issues.")
                    continue
            if problem_name == 'RDW2D51F':
                if comb[0] >= 512:
                    print(f"Skipping parameter combination {comb} for problem RDW2D51F due to known issues.")
                    continue
            if problem_name == 'RDW2D51U':
                if comb[0] >= 512:
                    print(f"Skipping parameter combination {comb} for problem RDW2D51U due to known issues.")
                    continue
            if problem_name == 'RDW2D52B':
                if comb[0] >= 512:
                    print(f"Skipping parameter combination {comb} for problem RDW2D52B due to known issues.")
                    continue
            if problem_name == 'RDW2D52F':
                if comb[0] >= 512:
                    print(f"Skipping parameter combination {comb} for problem RDW2D52F due to known issues.")
                    continue
            if problem_name == 'RDW2D52U':
                if comb[0] >= 512:
                    print(f"Skipping parameter combination {comb} for problem RDW2D52U due to known issues.")
                    continue
            if problem_name == 'ROSEPETAL':
                if comb[0] >= 10000:
                    print(f"Skipping parameter combination {comb} for problem ROSEPETAL due to known issues.")
                    continue
            if problem_name == 'TWOD':
                if comb[0] >= 79:
                    print(f"Skipping parameter combination {comb} for problem TWOD due to known issues.")
                    continue
            if problem_name == 'SENSORS':
                if comb[0] >= 1000:
                    print(f"Skipping parameter combination {comb} for problem SENSORS due to known issues.")
                    continue
            if problem_name == 'SOSQP1':
                if comb[0] >= 50000:
                    print(f"Skipping parameter combination {comb} for problem SOSQP1 due to known issues.")
                    continue
            if problem_name == 'SOSQP2':
                if comb[0] >= 50000:
                    print(f"Skipping parameter combination {comb} for problem SOSQP2 due to known issues.")
                    continue
            if problem_name == 'STCQP2':
                if comb[0] >= 16:
                    print(f"Skipping parameter combination {comb} for problem STCQP2 due to known issues.")
                    continue
            if problem_name == 'STNQP1':
                if comb[0] >= 16:
                    print(f"Skipping parameter combination {comb} for problem STNQP1 due to known issues.")
                    continue



            success, result = run_with_timeout(process_arg, (problem_name, dict(zip(para_names, comb))), timeout)
            # success, result = process_arg(problem_name, dict(zip(para_names, comb)))
            if not success or result is None:
                print(f"Failed to process problem {problem_name} with parameter combination: {comb}")
                continue

            successful_para_combinations.append(comb)
            info_single['dims'] += str(result['n']) + ' '
            info_single['mbs'] += str(result['mb']) + ' '
            info_single['mls'] += str(result['ml']) + ' '
            info_single['mus'] += str(result['mu']) + ' '
            info_single['mcons'] += str(result['mcon']) + ' '
            info_single['mlcons'] += str(result['mlcon']) + ' '
            info_single['mnlcons'] += str(result['mnlcon']) + ' '
            info_single['m_ubs'] += str(result['m_ub']) + ' '
            info_single['m_eqs'] += str(result['m_eq']) + ' '
            info_single['m_linear_ubs'] += str(result['m_linear_ub']) + ' '
            info_single['m_linear_eqs'] += str(result['m_linear_eq']) + ' '
            info_single['m_nonlinear_ubs'] += str(result['m_nonlinear_ub']) + ' '
            info_single['m_nonlinear_eqs'] += str(result['m_nonlinear_eq']) + ' '
            info_single['f0s'] += str(result['f0']) + ' '
        except TimeoutError:
            print(f"Timeout while processing problem {problem_name} with parameter combination: {comb}")
            timeout_problems.append(problem_name + f" with parameters {comb}")
        except Exception as e:
            print(f"Error while processing problem {problem_name} with parameter combination: {comb}: {e}")
        finally:
            try:
                pycutest_clear_cache(problem_name, **dict(zip(para_names, comb)))
            except:
                pass
            try:
                del p_param, success, result
            except:
                pass
            gc.collect()


    # Store the parameter combinations, e.g., "{'A': 1, 'N': 10}{'A': 2, 'N': 10}"
    arg_strs = ''
    for comb in successful_para_combinations:
        arg_str = '{' + ','.join([f"'{para_names[i]}':{comb[i]}" for i in range(len(para_names))]) + '}'
        arg_strs += arg_str
    info_single['argins'] = arg_strs.strip()

    info_single['dims'] = info_single['dims'].strip()
    info_single['mbs'] = info_single['mbs'].strip()
    info_single['mls'] = info_single['mls'].strip()
    info_single['mus'] = info_single['mus'].strip()
    info_single['mcons'] = info_single['mcons'].strip()
    info_single['mlcons'] = info_single['mlcons'].strip()
    info_single['mnlcons'] = info_single['mnlcons'].strip()
    info_single['m_ubs'] = info_single['m_ubs'].strip()
    info_single['m_eqs'] = info_single['m_eqs'].strip()
    info_single['m_linear_ubs'] = info_single['m_linear_ubs'].strip()
    info_single['m_linear_eqs'] = info_single['m_linear_eqs'].strip()
    info_single['m_nonlinear_ubs'] = info_single['m_nonlinear_ubs'].strip()
    info_single['m_nonlinear_eqs'] = info_single['m_nonlinear_eqs'].strip()
    info_single['f0s'] = info_single['f0s'].strip()

    print(f"Finished processing problem {problem_name} with parameters.")
    return info_single


if __name__ == "__main__":
    print(problem_names)

    # Save problem information into a csv file
    results = []
    for name in problem_names:
        print(f">>> STARTING: {name}")
        sys.stdout.flush()
        
        para_names, para_values, para_defaults = pycutest_get_sif_params(name)

        info = get_problem_info(name, known_feasibility, para_names=para_names, para_values=para_values, para_defaults=para_defaults)
        results.append(info)
        sys.stdout.flush()
        sys.stderr.flush()

    df = pd.DataFrame(results)

    def has_unknown_values(row):
        for value in row:
            if str(value).strip().lower() == 'unknown':
                return True
        return False
    unknown_mask = df.apply(has_unknown_values, axis=1)
    if unknown_mask.any():
        filtered_problems = df.loc[unknown_mask, 'problem_name'].tolist()
        print(f"Filtered out {len(filtered_problems)} problems with 'unknown' values:")
        for problem in filtered_problems:
            print(f"  - {problem}")
    df_clean = df[~unknown_mask]

    df_clean.to_csv(os.path.join(saving_path, f'probinfo_pycutest_block{current_block}.csv'), index=False, na_rep='nan')

    # Save 'feasibility' to txt file in the one line format with space separated values
    feasibility_file = os.path.join(saving_path, 'feasibility_pycutest.txt')
    with open(feasibility_file, 'w') as f:
        f.write(' '.join(feasibility))

    # Save 'timeout_problems' to txt file in the one line format with space separated values
    timeout_file = os.path.join(saving_path, 'timeout_problems_pycutest.txt')
    with open(timeout_file, 'w') as f:
        f.write(' '.join(timeout_problems))

    print("Script completed successfully.")

    # Close the log file
    log_file.close()

    sys.stdout = sys.__stdout__  # Reset stdout to default
    sys.stderr = sys.__stderr__  # Reset stderr to default
