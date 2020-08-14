#
# Copyright (c) 2018, 2020 Oracle and/or its affiliates.  All rights reserved.
#
# Licensed under the Universal Permissive License v 1.0 as shown at
#  https://oss.oracle.com/licenses/upl/

#
# Parameters used by test code -- Cloud Simulator Configuration
#
# This file is configured for the unit tests to be run against a Cloud Simulator
# instance. The simulator is used so that limits that exist in the cloud service
# are not involved and there is no cost involved in running the unit tests.
#
# The default settings below are sufficient if the Cloud Simulator has been
# started on the endpoint, localhost:8080, which is its default. If not, the
# parameters in this file should be changed as needed. Please see sample config
# options in: config_cloudsim.py and config_onprem.py, change the parameters
# in those files, then copy the content to this file.
#

# The endpoint to use to connect to the service. This endpoint is for a Cloud
# Simulator running on its default port (8080) on the local machine.
endpoint = 'localhost:8080'

# The server type.
server_type = 'cloudsim'

# Cloud Simulator version. Use None to test with the latest Cloud Simulator
# version, a specified version should be like "1.4.0".
version = None
