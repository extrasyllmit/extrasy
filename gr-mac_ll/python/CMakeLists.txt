#
# This file is part of ExtRaSy
#
# Copyright (C) 2013-2014 Massachusetts Institute of Technology
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# 
# This file incorporates work covered by the following copyright:
#
#
# Copyright 2011 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

########################################################################
# Include python install macros
########################################################################
include(GrPython)
if(NOT PYTHONINTERP_FOUND)
    return()
endif()

INCLUDE(LL_Version)   #setup version num

set_source_files_properties( ${CMAKE_BINARY_DIR}/python/version.py 
	PROPERTIES GENERATED true)

########################################################################
# Add version info
########################################################################
CONFIGURE_FILE(
    ${CMAKE_CURRENT_SOURCE_DIR}/version.py
    ${CMAKE_BINARY_DIR}/python/version.py
@ONLY)

########################################################################
# Install python sources
########################################################################
GR_PYTHON_INSTALL(
    FILES
    __init__.py
#    mac_sm.py
    sm.py
#    pkt_conversions.py
    traffic_gen.py
    tdma_mac_sm.py
    tdma_controller.py
    SlotManager.py
    dataInt.py
#    Agent.py
#    agent_visualizations.py
    learning_agent.py
#    mdp.py
    node_agents.py
#    utils.py
    rl_agent_utils.py
    sequential_agent_utils.py
    ${CMAKE_BINARY_DIR}/python/version.py
    DESTINATION ${GR_PYTHON_DIR}/mac_ll
)

########################################################################
# Handle the unit tests
########################################################################
include(GrTest)

set(GR_TEST_TARGET_DEPS gnuradio-mac_ll)
set(GR_TEST_PYTHON_DIRS ${CMAKE_BINARY_DIR}/swig)
GR_ADD_TEST(qa_csma_ca_arq_components ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_ca_arq_components.py)
GR_ADD_TEST(qa_csma_ca_arq ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_ca_arq.py)
GR_ADD_TEST(qa_csma_ca_components ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_ca_components.py)
GR_ADD_TEST(qa_csma_ca ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_ca.py)
GR_ADD_TEST(qa_csma_arq_components ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_arq_components.py)
GR_ADD_TEST(qa_csma_arq ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_arq.py)
GR_ADD_TEST(qa_csma_components ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma_components.py)
GR_ADD_TEST(qa_csma ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_csma.py)
GR_ADD_TEST(qa_tdma_mobile_sm ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_tdma_mobile_sm.py)
GR_ADD_TEST(qa_tdma_base_sm ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_tdma_base_sm.py)
GR_ADD_TEST(qa_reinforcement_learner ${PYTHON_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/qa_reinforcement_learner.py)

