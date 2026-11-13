"""Scheduler adapter: the only door between the harness and a scheduler.

A real adapter (Control-M Automation API, AutoSys, JS7...) implements the same verbs:
  reads:   list_jobs, sysout, waiting_info, table_count, table_dupes, get_alerts, get_clock
  actions: hold, free, rerun, run_cleanup, set_to_ok, add_event
Every executed action is recorded in `trace`, so a run can be replayed without a model.
"""
import copy

from . import repo as _repo
from .emulator import ACTION_VERBS, READ_VERBS


class RepoAdapter:
    """Same contract for the definition side: reads, raw actions, and a replayable trace."""

    def __init__(self, repo):
        self.repo, self.trace = repo, []

    def call(self, verb, **kw):
        if verb in _repo.READ_VERBS:
            return copy.deepcopy(getattr(self.repo, verb)(**kw))
        if verb in _repo.ACTION_VERBS:
            r = self.repo.act(verb, **copy.deepcopy(kw))
            self.trace.append([verb, copy.deepcopy(kw), r["ok"]])
            return r
        raise ValueError(f"unknown verb: {verb}")


class EmulatorAdapter:
    def __init__(self, emu):
        self.emu, self.trace = emu, []

    def call(self, verb, **kw):
        if verb in READ_VERBS:
            return copy.deepcopy(getattr(self.emu, verb)(**kw))
        if verb in ACTION_VERBS:
            r = self.emu.act(verb, **kw)
            self.trace.append([verb, kw, r["ok"]])
            return r
        raise ValueError(f"unknown verb: {verb}")
