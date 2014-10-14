#
# Copyright 2010-2012 Ettus Research LLC
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

########################################################################
INCLUDE(GrPython) #requires python for parsing


########################################################################
# Version information discovery through git log
########################################################################

#grab the git branch name for the current head
EXECUTE_PROCESS(
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMAND git rev-parse --symbolic-full-name --abbrev-ref HEAD
    OUTPUT_VARIABLE _git_describe OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _git_describe_result
)

#only set the build info on success
IF(_git_describe_result EQUAL 0)
    EXECUTE_PROCESS(
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMAND ${PYTHON_EXECUTABLE} -c "print '${_git_describe}'.strip()"
        OUTPUT_VARIABLE GIT_BRANCH OUTPUT_STRIP_TRAILING_WHITESPACE
    )
ENDIF()

#grab the git commit id for the current head
EXECUTE_PROCESS(
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMAND git describe --always --dirty
    OUTPUT_VARIABLE _git_describe OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE _git_describe_result
)

#only set the build info on success
IF(_git_describe_result EQUAL 0)
    EXECUTE_PROCESS(
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMAND ${PYTHON_EXECUTABLE} -c "print '${_git_describe}'.strip()"
        OUTPUT_VARIABLE GIT_HASH OUTPUT_STRIP_TRAILING_WHITESPACE
    )
ENDIF()


##only set the build info on success
#IF(_git_describe_result EQUAL 0)
#    EXECUTE_PROCESS(
#        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
#        COMMAND ${PYTHON_EXECUTABLE} -c "print '${_git_describe}'.split('-')[1]"
#        OUTPUT_VARIABLE UHD_GIT_COUNT OUTPUT_STRIP_TRAILING_WHITESPACE
#    )
#    EXECUTE_PROCESS(
#        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
#        COMMAND ${PYTHON_EXECUTABLE} -c "print '${_git_describe}'.split('-')[2]"
#        OUTPUT_VARIABLE UHD_GIT_HASH OUTPUT_STRIP_TRAILING_WHITESPACE
#    )
#ENDIF()

IF(NOT GIT_BRANCH)
    SET(GIT_BRANCH "unknown")
ENDIF()

IF(NOT GIT_HASH)
    SET(GIT_HASH "unknown")
ENDIF()


########################################################################
SET(LL_VERSION "${GIT_BRANCH}-${GIT_HASH}")

