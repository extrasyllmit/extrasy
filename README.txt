################################################################################
# Experimental Radio System   (ExtRaSy)
################################################################################

ExtRaSy enables network communications among software-defined radios running GNU Radio. In particular, ExtRaSy provides Physical Layer enhancements, a Link Layer, and a Network Layer interface to allow multiple GNU Radio nodes to communicate traffic. This functionality is highly configurable via more than 100 user-tunable parameters. ExtRaSy also includes performance logging capabilities and performance analysis functionality.

ExtRaSy allows the user to configuring each node’s Radio Transceiver, Physical Layer, Link Layer, and a Tun/Tap interface to the Network Layer. The user’s application can then communicate its traffic to and from other nodes in the network by accessing the Tun/Tap interface.

Five Link Layer protocols are included with ExtRaSy:  Carrier Sense Multiple Access (CSMA), Time Division Multiple Access (TDMA), TDMA with Frequency Hopping (FH), and two Dynamic Spectrum Access (DSA) protocols.

ExtRaSy also includes the following features and tools to support development and testing:
•	Node configuration from file or command line to support test automation
•	Logging of all transmitted and received Link Layer packet metadata and state machine activity
•	An infinite backlog traffic generator embedded in the Link Layer for use as an alternative to the Tun/Tap Interface. 
•	Functions to post-process logs and plot results
•	A channel sounding tool for characterizing pathloss and SNR between all nodes simultaneously
•	Functions for testing agent designs

The following four ready-to-run example networks are included with ExtRaSy:
•	A simple TDMA network
•	A TDMA network with a frequency hopping pattern
•	A DSA network that uses error rate feedback to make reflexive spectrum access decisions 
•	A DSA network that uses a reinforcement learning agent to make spectrum access decisions


################################################################################
# Installation
################################################################################

Please see ExtRaSy_Installation_Notes.txt  


################################################################################
# Directory Table of Contents
################################################################################

AUTHORS              contributors to ExtRaSy
README.txt           this document
channel_char.txt     documentation on the channel sounding tool
/apps                source for ExtRaSy "apps" (including the four ready-to-run example
                     networks mentioned above)
/gr-channel_charac   source for the channel sounding tool
/gr-digital_ll       source for Physical Layer functionality
/gr-maac_ll          source for Link Layer functionality
/configs             ready-to-run examples with instructions and configuration files
                     See tdmaTemplateCommented.ini for documentation on each parameter
                     in the configuration files.
/matlab              functions for post-processing logs generated when running apps
/results-archive     an archive of logs and results from running the examples


################################################################################
# About the development platform
################################################################################

ExtRaSy was developed and tested with the following hardware.
•	Radio frontend specs:
o	Ettus Research USRP N210 (hardware rev. 4, firmware version 12.3) 
o	Ettus Research SBX daughterboard (rev. 3)
o	Jackson Labs GPS module for USRP N210
•	Host computers specs:
o	Intel Xeon E3-1270v2, 3.50 GHz, 8M Cache
o	16GB RAM (1333MHz)

ExtRaSy was developed and tested on host machines installed with the following software:
•	Ubuntu 12.04 LTS
•	GNU Radio 3.6.3
•	GNU C++ compiler (version 4.6.3)
•	GNU Standard C++ Library
•	The GNU C Library
•	Boost (version  1.48.0)
•	Ettus Research USRP Hardware Driver (version UHD_003.005.000-26-gb65a3924)
•	wxPython
•	Numpy
•	Matplotlib
•	Reed-Solomon Python extension module
•	XML MATLAB toolkit
•	lxml
•	JSONlab


################################################################################
# Limitations
################################################################################

ExtRaSy was a rapid developed effort to prove fundamental concepts in GNU Radio. As a result, the implementation has quirks and there is much potential for improving performance. We hope this only encourages you to improve it and continue pushing the envelope for what can be done in the GNU Radio framework. 

Here are some known limitations of the software:

•	Radio Frontend Hopping and Radio Frontend Power Control should not be invoked simultaneously for the tdma-berf protocol.

•	The channel sounding tool is calibrated for the Ettus Research SBX daughterboard (rev. 3). The calibration table would need to be replaced if the tool is to be used with other radio frontends.

•	The CSMA network is currently non-functional. /apps/csma_node.py is provided as example code for the interim.

################################################################################
% Copyright 2013-2014 Massachusetts Institute of Technology
% 
% This program is free software: you can redistribute it and/or modify
% it under the terms of the GNU General Public License as published by
% the Free Software Foundation, either version 2 of the License, or
% (at your option) any later version.
% 
% This program is distributed in the hope that it will be useful,
% but WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
% GNU General Public License for more details.
% 
% You should have received a copy of the GNU General Public License
% along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################
