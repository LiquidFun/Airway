#!/usr/bin/env python3

from py2cytoscape.data.cyrest_client import CyRestClient
import sys
import time
from pathlib import Path

cy = CyRestClient()
cy.session.delete()

pathsToGraphs = sorted(Path(sys.argv[1]).glob("3183090/*.graphml"))

cyNets = []
i = 0
for path in pathsToGraphs:
    cyNets.append(cy.network.create_from(str(path), collection="net-" + str(i)))
    i = i + 1
    time.sleep(0.2)
