# -*- coding: utf-8 -*-
"""RCC Abstract Class - A base class for all other RCC implementation

:Author: Peter Lightbody <plightbody@lincoln.ac.uk>
:Organization: University of Lincoln
:Date: 10 Aug 2015
:Version: 0.1
:Status: Development
:Copyright: STRANDS default

:Notes: future extension to handle polygons, to do that use matplotlib.path.Path.contains_points
        although might want to have a read on the following also...
        http://matplotlib.1069221.n5.nabble.com/How-to-properly-use-path-Path-contains-point-td40718.html

"""
from abc import abstractmethod, ABCMeta
from qsrlib_qsrs.qsr_abstractclass import QSR_Abstractclass
from qsrlib_io.world_qsr_trace import *
from exceptions import Exception, AttributeError
import numpy as np

class QSR_RCC_Abstractclass(QSR_Abstractclass):
    """Abstract class for the QSR makers"""
    __metaclass__ = ABCMeta

    def __init__(self):
        self.all_possible_relations = []

    def custom_checks_for_qsrs_for(self, qsrs_for, error_found):
        """qsrs_for must be tuples of two objects.

        :param qsrs_for: list of strings and/or tuples for which QSRs will be computed
        :param error_found: if an error was found in the qsrs_for that violates the QSR rules
        :return: qsrs_for, error_found
        """
        for p in list(qsrs_for):
            if (type(p) is not tuple) and (type(p) is not list) and (len(p) != 2):
                qsrs_for.remove(p)
                error_found = True
        return qsrs_for, error_found

    def make(self, *args, **kwargs):
        """Make the QSRs

        :param args: not used at the moment
        :param kwargs:
                        - input_data: World_Trace
        :return: World_QSR_Trace
        """
        input_data = kwargs["input_data"]
        include_missing_data = kwargs["include_missing_data"]
        ret = World_QSR_Trace(qsr_type=self._unique_id)
        for t in input_data.get_sorted_timestamps():
            world_state = input_data.trace[t]
            timestamp = world_state.timestamp
            if kwargs["qsrs_for"]:
                qsrs_for, error_found = self.check_qsrs_for_data_exist(world_state.objects.keys(), kwargs["qsrs_for"])
            else:
                qsrs_for = self.__return_all_possible_combinations(world_state.objects.keys())
            if qsrs_for:
                for p in qsrs_for:
                    between = str(p[0]) + "," + str(p[1])
                    bb1 = world_state.objects[p[0]].return_bounding_box_2d()
                    bb2 = world_state.objects[p[1]].return_bounding_box_2d()
                    qsr = QSR(timestamp=timestamp, between=between,
                              qsr=self.handle_future(kwargs["future"], self.__compute_qsr(bb1, bb2), self._unique_id))
                    ret.add_qsr(qsr, timestamp)
            else:
                if include_missing_data:
                    ret.add_empty_world_qsr_state(timestamp)
        return ret

    def __return_all_possible_combinations(self, objects_names):
        if len(objects_names) < 2:
            return []
        ret = []
        for i in objects_names:
            for j in objects_names:
                if i != j:
                    ret.append((i, j))
        return ret

    def __compute_qsr(self, bb1, bb2, q=0.0):
        """Return symmetrical RCC8 relation
            :param bb1: diagonal points coordinates of first bounding box (x1, y1, x2, y2)
            :param bb2: diagonal points coordinates of second bounding box (x1, y1, x2, y2)
            :param q: quantisation factor for all objects
            :return: an RCC8 relation from the following:
                'dc'     bb1 is disconnected from bb2
                'ec'     bb1 is externally connected with bb2
                'po'     bb1 partially overlaps bb2
                'eq'     bb1 equals bb2
                'tpp'    bb1 is a tangential proper part of bb2
                'ntpp'   bb1 is a non-tangential proper part of bb2
                'tppi'   bb2 is a tangential proper part of bb1
                'ntppi'  bb2 is a non-tangential proper part of bb1
                 +-------------+         +-------------+
                 |a            |         |c            |
                 |             |         |             |
                 |     bb1     |         |     bb2     |
                 |             |         |             |
                 |            b|         |            d|
                 +-------------+         +-------------+
        """

        # CALCULATE EQ
        # Is object1 equal to object2
        if(bb1 == bb2):
            return "eq"

        ax, ay, bx, by = bb1
        cx, cy, dx, dy = bb2

        # Are objects disconnected?
        # Cond1. If A's left edge is to the right of the B's right edge, - then A is Totally to right Of B
        # Cond2. If A's right edge is to the left of the B's left edge, - then A is Totally to left Of B
        # Cond3. If A's top edge is below B's bottom edge, - then A is Totally below B
        # Cond4. If A's bottom edge is above B's top edge, - then A is Totally above B
        
        #    Cond1           Cond2          Cond3         Cond4
        if (ax-q > dx+q) or (bx+q < cx-q) or (ay-q > dy+q) or (by+q < cy-q):
            return "dc"

        # Is one object inside the other ()
        BinsideA = (ax <= cx) and (ay <= cy) and (bx >= dx) and (by >= dy)
        AinsideB = (ax >= cx) and (ay >= cy) and (bx <= dx) and (by <= dy)

        # Do objects share an X or Y (but are not necessarily touching)
        sameX = (abs(ax - cx)<=q) or (abs(ax - dx)<=q) or (abs(bx - cx)<=q) or (abs(bx - dx)<=q)
        sameY = (abs(ay - cy)<=q) or (abs(ay - dy)<=q) or (abs(by - cy)<=q) or (abs(by - dy)<=q)
        
        if AinsideB and (sameX or sameY):
            return "tpp"

        if BinsideA and (sameX or sameY):
            return "tppi"

        if AinsideB:
            return "ntpp"

        if BinsideA:
            return "ntppi"

        similarX = (abs(ax - cx)<q) or (abs(ax - dx)<q) or (abs(bx - cx)<q) or (abs(bx - dx)<q)
        similarY = (abs(ay - cy)<q) or (abs(ay - dy)<q) or (abs(by - cy)<q) or (abs(by - dy)<q)

        # Are objects touching?
        # Cond1. If A's left edge is equal to B's right edge, - then A is to the right of B and touching
        # Cond2. If A's right edge is qual to B's left edge, - then A is to the left of B and touching
        # Cond3. If A's top edge equal to B's bottom edge, - then A is below B and touching
        # Cond4. If A's bottom edge equal to B's top edge, - then A is above B and touching

        # If quantisation overlaps, but bounding boxes do not then edge connected,
        # include the objects edges, but do not include the quantisation edge
        if ((cx-q) <= (bx+q)) and ((cx-q) >= (bx)) or \
           ((dx+q) >= (ax-q)) and ((dx+q) <= (ax)) or \
           ((cy-q) <= (by+q)) and ((cy-q) >= (by)) or \
           ((dy+q) >= (ay-q)) and ((dy+q) <= (ay)):
            return "ec"

        # If none of the other conditions are met, the objects must be parially overlapping
        return "po"

    @abstractmethod
    def convert_to_current_rcc(self, qsr):
        """Overwrite this function to filter and return only the relations
        coresponding to the particular RCC version you are using.
        
        Example for RCC2: return qsr if qsr =="dc" else "c"

        :param qtc: The RCC8 relation between two objects
        :return: The part of the tuple you would to have as a result
        """
        raise NotImplementedError("Filter RCC results using convert_to_current_rcc function")