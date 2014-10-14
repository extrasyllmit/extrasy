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
# Setup library
########################################################################
include(GrPlatform) #define LIB_SUFFIX

add_library(gnuradio-channel_charac SHARED channel_charac_signal_gen.cc channel_charac_test.cc)
target_link_libraries(gnuradio-channel_charac ${Boost_LIBRARIES} ${GRUEL_LIBRARIES} ${GNURADIO_CORE_LIBRARIES})
set_target_properties(gnuradio-channel_charac PROPERTIES DEFINE_SYMBOL "gnuradio_channel_charac_EXPORTS")

########################################################################
# Install built library files
########################################################################
install(TARGETS gnuradio-channel_charac
    LIBRARY DESTINATION lib${LIB_SUFFIX} # .so/.dylib file
    ARCHIVE DESTINATION lib${LIB_SUFFIX} # .lib file
    RUNTIME DESTINATION bin              # .dll file
)

########################################################################
# Build and register unit test
########################################################################
find_package(Boost COMPONENTS unit_test_framework)

include(GrTest)
set(GR_TEST_TARGET_DEPS gnuradio-channel_charac)
#turn each test cpp file into an executable with an int main() function
add_definitions(-DBOOST_TEST_DYN_LINK -DBOOST_TEST_MAIN)

