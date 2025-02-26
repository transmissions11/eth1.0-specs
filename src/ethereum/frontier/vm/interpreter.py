"""
Ethereum Virtual Machine (EVM) Interpreter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. contents:: Table of Contents
    :backlinks: none
    :local:

Introduction
------------

A straightforward interpreter that executes EVM code.
"""

from typing import List, Tuple

from ethereum.base_types import U256, Uint
from ethereum.frontier.vm.error import InvalidOpcode

from ..eth_types import Address, Log
from . import Environment, Evm
from .instructions import Ops, op_implementation


def process_call(
    caller: Address,
    target: Address,
    data: bytes,
    value: U256,
    gas: U256,
    depth: Uint,
    env: Environment,
) -> Tuple[U256, List[Log]]:
    """
    Executes a call from the `caller` to the `target` in a new EVM instance.

    Parameters
    ----------
    caller :
        Account which initiated this call.

    target :
        Account whose code will be executed.

    data :
        Array of bytes provided to the code in `target`.

    value :
        Value to be transferred.

    gas :
        Gas provided for the code in `target`.

    depth :
        Number of call/contract creation environments on the call stack.

    env :
        External items required for EVM execution.

    Returns
    -------
    output : `Tuple[U256, List[eth1spec.eth_types.Log]]`
        The tuple `(gas_left, logs)`, where `gas_left` is the remaining gas
        after execution, and logs is the list of `eth1spec.eth_types.Log`
        generated during execution.
    """
    evm = Evm(
        pc=Uint(0),
        stack=[],
        memory=bytearray(),
        code=env.state[target].code,
        gas_left=gas,
        current=target,
        caller=caller,
        data=data,
        value=value,
        depth=depth,
        env=env,
        refund_counter=Uint(0),
        running=True,
    )

    logs: List[Log] = []

    if evm.value != 0:
        evm.env.state[evm.caller].balance -= evm.value
        evm.env.state[evm.current].balance += evm.value

    while evm.running:
        try:
            op = Ops(evm.code[evm.pc])
        except ValueError:
            raise InvalidOpcode(evm.code[evm.pc])

        op_implementation[op](evm)
        evm.pc += 1

        if evm.pc >= len(evm.code):
            evm.running = False

    gas_used = gas - evm.gas_left
    refund = min(gas_used // 2, evm.refund_counter)

    return evm.gas_left + refund, logs
