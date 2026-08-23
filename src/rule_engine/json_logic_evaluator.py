"""
json_logic_evaluator.py
Avaliador nativo e determinístico de JSON-Logic com suporte completo a operadores relacionais,
lógicos, de coleção e nulos. 100% padrão Python sem dependências externas.
"""

from typing import Any, Dict, List, Union

def evaluate_json_logic(logic: Any, data: Dict[str, Any]) -> Any:
    """
    Avalia recursivamente uma expressão JSON-Logic contra um dicionário de dados.
    """
    if not isinstance(logic, dict):
        return logic

    if not logic:
        return {}

    operator, values = list(logic.items())[0]

    if not isinstance(values, list) and not isinstance(values, tuple):
        values = [values]

    # 1. Recuperação de Variáveis: {"var": "caminho.da.chave", "default": val}
    if operator == "var":
        var_path = values[0] if len(values) > 0 else ""
        default_val = values[1] if len(values) > 1 else None
        
        if not var_path:
            return data
            
        return _get_var_value(data, str(var_path), default_val)

    # 2. Operadores Lógicos
    if operator == "and":
        last_val = True
        for v in values:
            res = evaluate_json_logic(v, data)
            if not _is_truthy(res):
                return False
            last_val = res
        return True

    if operator == "or":
        for v in values:
            res = evaluate_json_logic(v, data)
            if _is_truthy(res):
                return True
        return False

    if operator == "!":
        res = evaluate_json_logic(values[0], data)
        return not _is_truthy(res)

    if operator == "!!":
        res = evaluate_json_logic(values[0], data)
        return _is_truthy(res)

    # 3. Operadores Relacionais e Numéricos
    eval_values = [evaluate_json_logic(v, data) for v in values]

    if operator in ("==", "==="):
        return eval_values[0] == eval_values[1] if len(eval_values) >= 2 else False

    if operator in ("!=", "!=="):
        return eval_values[0] != eval_values[1] if len(eval_values) >= 2 else True

    if operator == "<":
        return eval_values[0] < eval_values[1] if len(eval_values) >= 2 and eval_values[0] is not None and eval_values[1] is not None else False

    if operator == "<=":
        return eval_values[0] <= eval_values[1] if len(eval_values) >= 2 and eval_values[0] is not None and eval_values[1] is not None else False

    if operator == ">":
        return eval_values[0] > eval_values[1] if len(eval_values) >= 2 and eval_values[0] is not None and eval_values[1] is not None else False

    if operator == ">=":
        return eval_values[0] >= eval_values[1] if len(eval_values) >= 2 and eval_values[0] is not None and eval_values[1] is not None else False

    # 4. Operadores de Coleção / String
    if operator == "in":
        item = eval_values[0]
        container = eval_values[1]
        if container is None or item is None:
            return False
        return item in container

    if operator == "contains":
        container = eval_values[0]
        item = eval_values[1]
        if container is None or item is None:
            return False
        return item in container

    # 5. Operador Condicional If-Then-Else: {"if": [cond, then, else]}
    if operator == "if":
        for i in range(0, len(values) - 1, 2):
            if _is_truthy(evaluate_json_logic(values[i], data)):
                return evaluate_json_logic(values[i + 1], data)
        if len(values) % 2 == 1:
            return evaluate_json_logic(values[-1], data)
        return None

    raise ValueError(f"Operador JSON-Logic não suportado: '{operator}'")

def _get_var_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    
    # 1. Checagem direta (chave plana)
    if path in data:
        return data[path]

    # 2. Checagem aninhada (dot notation)
    keys = path.split(".")
    curr = data
    for k in keys:
        if isinstance(curr, dict) and k in curr:
            curr = curr[k]
        else:
            return default
    return curr

def _is_truthy(val: Any) -> bool:
    if val is None or val is False:
        return False
    if isinstance(val, (int, float)) and val == 0:
        return False
    if isinstance(val, (str, list, dict)) and len(val) == 0:
        return False
    return True
