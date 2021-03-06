# -*- coding: utf-8 -*-

"""
scheduler.py
=====

This module contains the `Scheduler` class which is a base class for various
types of schedulers. The `VirtualTimeSyncScheduler` is implemneted for now.

"""

__all__ = ["Scheduler", "VirtualTimeSyncScheduler", "VirtualTimeScheduler", "RealTimeSyncScheduler"]

from .utils import *

from abc import ABCMeta, abstractmethod
import copy
import time
import numpy

import future
import queue

class Scheduler(object):
    """
    This class is an abstract class for creating `Scheduler`s. Subclasses must
    override the `step()` method to specify its implementation.
    """

    __metaclass__ = ABCMeta

    def __init__(self):
        """ Create a new `Scheduler` instance.

        Args:
          None.

        Returns:
          Scheduler: A new `Scheduler` instance.

        """

        super(Scheduler, self).__init__()
        self.num_steps = 0
        self.current_time = 0.0
        self.components = []

    def reset(self):
        """ Reset the `Scheduler`.

        Args:
          None.

        Returns:
          None.

        """

        self.num_steps = 0
        self.current_time = 0.0
        self.components = []

    def update(self, ca):
        """ Update the `Scheduler` for given cognitive architecture (ca)

        Args:
          ca (Agent): a target to update.

        Returns:
          None.

        """

        self.components = ca.get_all_components()

    @abstractmethod
    def step(self):
        """ Step over a single iteration

        Args:
          None.

        Returns:
          float: the current time of the `Scheduler`.

        """

        pass

class VirtualTimeSyncScheduler(Scheduler):
    """
    `VirtualTimeSyncScheduler` is a `Scheduler` implementation for virutal time
    in a synced manner.
    """

    def __init__(self, interval=1.0):
        """ Create a new `VirtualTimeSyncScheduler` Instance.

        Args:
          interval (float): interval in seconds between each step

        Returns:
          VirtualTimeSyncScheduler: A new `VirtualTimeSyncScheduler` instance.

        """

        super(VirtualTimeSyncScheduler, self).__init__()
        self.interval = interval

    def step(self):
        """ Step by the internal interval.

        The methods `input()`, `fire()`, and `output()` are synchronously
        called and the time is incremented by the given interval for each
        step.

        Args:
          None.

        Returns:
          float: the current time of the `Scheduler`.

        """

        for component in self.components:
            component.input(self.current_time)

        for component in self.components:
            component.fire()

        self.current_time = self.current_time + self.interval

        for component in self.components:
            component.output(self.current_time)

        return self.current_time

class VirtualTimeScheduler(Scheduler):
    """
    `VirtualTimeScheduler` is a `Scheduler` implementation for virutal time.
    """

    class Event(object):
        """
        `Event` is a queue object for `PriorityQueue` in VirtualTimeScheduler.
        """

        def __init__(self, time, component):
            """ Create a new `Event` instance.

            Args:
              time (float): the time of the `Event`.
              component (Component): `Component` to be handled.

            Returns:
              Component: a new `Component` instance.

            """

            super(VirtualTimeScheduler.Event, self).__init__()
            self.time = time
            self.component = component

        def __lt__(self, other):
            return self.time < other.time;

    def __init__(self):
        """ Create a new `Event` instance.

        Args:
          time (float): the time of the `Event`.
          component (Component): `Component` to be handled.

        Returns:
          Component: a new `Component` instance.

        """

        super(VirtualTimeScheduler, self).__init__()
        self.event_queue = queue.PriorityQueue()

    def update(self, ca):
        """ Update the `Scheduler` for given cognitive architecture (ca)

        Args:
          ca (Agent): a target to update.

        Returns:
          None.

        """

        super(VirtualTimeScheduler, self).update(ca)
        for component in self.components:
            component.input(self.current_time)
            component.fire()
            self.event_queue.put(VirtualTimeScheduler.Event(component.offset + component.last_input_time + component.interval, component))

    def step(self):
        """ Step by the internal interval.

        An event is dequeued and `output()`, `input()`, and `fire()` are called
        for the `Component` of interest.

        Args:
          None.

        Returns:
          float: the current time of the `Scheduler`.

        """

        e = self.event_queue.get()
        self.current_time = e.time
        component = e.component
        component.output(self.current_time)
        component.input(self.current_time)
        component.fire()

        self.event_queue.put(VirtualTimeScheduler.Event(self.current_time + component.interval, component))

        return self.current_time

class RealTimeSyncScheduler(Scheduler):
    """
    `RealTimeSyncScheduler` is a `Scheduler` implementation for real time
    in a synced manner.
    """

    def __init__(self, interval=1.0):
        """ Create a new `RealTimeSyncScheduler` Instance.

        Args:
          interval (float): minimu interval in seconds between input and output of the modules.

        Returns:
          RealTimeSyncScheduler: A new `RealTimeSyncScheduler` instance.

        """

        self.last_input_time = -1.0
        self.last_output_time = -1.0
        self.last_spent = -1.0
        self.last_dt = -1.0

        super(RealTimeSyncScheduler, self).__init__()
        self.set_interval(interval)


    def reset():
        super(RealTimeSyncScheduler, self).reset()
        self.set_interval(1.0)


    def set_interval(self, interval):
        self.interval = float(interval)
        assert self.interval > 0.0

    def step(self):
        """ Step by the internal interval.

        The methods `input()`, `fire()`, and `output()` are synchronously
        called for all components.

        The time when it started calling input() and output() of the 
        components is stored in self.last_input_time and 
        self.last_output_time, respectively.

        self.interval sets the *minimum* interval between the point in
        time when input() is called and when output() is called.
        The actual interval between input() and output() will 
        always be longer than self.interval, although the scheduler
        tries to make the discrepancy minimum.

        When calling fire() of the components takes longer than the
        set interval, calling output() of the components will be 
        later than the scheduled time self.input_time + self.interval.
        In this case, self.lagged will be set True.

        During the execution of this method, it will also set self.last_spent,
        which will be the time spent until all components are fired
        after self.last_input_time is set.

        Args:
          None.

        Returns:
          float: the current time of the `Scheduler`.

        """

        self.last_input_time = current_time()
        self.current_time = self.last_input_time

        for component in self.components:
            component.input(self.last_input_time)

        for component in self.components:
            component.fire()

        self.last_spent = current_time() - self.last_input_time
        last_dt = self.interval - self.last_spent

        self.lagged = False
        if last_dt > 0.0:
            time.sleep(last_dt)
        elif last_dt < 0.0:
            self.lagged = True

        self.last_output_time = current_time()
        self.current_time = self.last_output_time

        for component in self.components:
            component.output(self.last_output_time)

        self.last_output_time = current_time()
        self.current_time = self.last_output_time

        return self.current_time
