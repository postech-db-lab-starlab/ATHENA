from itertools import combinations, chain
from networkx.utils import pairwise, not_implemented_for
import networkx as nx
import logging as log

from networkx.algorithms.approximation.steinertree import steiner_tree
from utils import PriorityQueue
#import matplotlib.pyplot as plt 

class ITreeGenerator():
    def __init__(self, onto_concepts):
        self.onto_graph = nx.DiGraph()
        self.ontologyToGraph(onto_concepts)

    def ontologyToGraph(self, onto_concepts):
        self.onto_graph.add_nodes_from(onto_concepts)
        
        for name, concept in onto_concepts.items():
            # Inheritance edge
            if concept.is_a:
                self.onto_graph.add_edge(name, concept.is_a.name, rname='is-a', weight=0)
            
            # Property node and edge
            for ppty in concept.properties:
                p_name = name + '.' + ppty
                self.onto_graph.add_node(p_name)
                self.onto_graph.add_edge(name, p_name, rname='property', weight=1)
            
            # Membership edge
            for parent in concept.unionOf:
                self.onto_graph.add_edge(name, parent.name, rname='unionOf', weight=0)

            # Functional edge
            for r_name, node_to in concept.relationships.items():
                new_name = name + '.' + r_name
                self.onto_graph.add_edge(name, node_to, rname=new_name, weight=1)

    def getITree(self, selected_set):
        graph = self.onto_graph.copy()

        concepts = []
        properties = []
        relationships = []
        for element in selected_set:
            if element[1] == 0:
                if element[2] == 0:
                    concepts += [element[3]]
                elif element[2] == 1:
                    properties += [element[3] + '.' + element[4]]
                else:
                    node1 = None
                    node2 = None
                    for tmp in selected_set:
                        if tmp[0] == element[7]:
                            node1 = tmp[3]
                            node1 += '.' + tmp[4] if tmp[4] else ''
                        elif tmp[0] == element[8]:
                            node2 = tmp[3]
                            node2 += '.' + tmp[4] if tmp[4] else ''
                    rname = element[3] + '.' + element[5]
                    relationships += [(node1, rname, node2)]

            elif element[1] == 1:
                properties += [element[3] + '.' + element[4]]
            else:
                log.error('Parsing Error...')
                exit(-1)

        nodes = concepts + properties
        self.fixWeight(graph, relationships)
        self.setInheritanceConstraint(graph, concepts)

        iTree = self.getModifiedSteinerTree(graph, nodes, relationships)

        # Check if iTree is connected
        if len(iTree.edges) + 1 != len(iTree.nodes):
            return None

        # Check if every node is reachable from root
        iRoot = self.getRoot(iTree)
        for node in iTree.nodes:
            paths = nx.all_simple_paths(iTree, iRoot, node)
            paths = [path for path in paths]
            if iRoot != node and not paths:
                return None

        return iTree

    def fixWeight(self, graph, relationships):
        rnames = nx.get_edge_attributes(graph, 'rname')
        for edge in graph.edges:
            name = rnames[edge]
            for r in relationships:
                if name == r[1]:
                    graph.edges[edge[0], edge[1]]['weight'] = 0

    def setInheritanceConstraint(self, graph, concepts):
        rnames = nx.get_edge_attributes(graph, 'rname')
        for node in graph.nodes:
            if node in concepts:
                for edge in graph.in_edges(node):
                    name = rnames[edge]
                    if name == 'is-a' or name == 'unionOf':
                        graph.remove_edge(edge)

    def getModifiedSteinerTree(self, graph, steiner_nodes, steiner_edges):
        biGraph = self.bidirected(graph)

        M = self.metric_closure(biGraph, weight='weight')
        H = M.subgraph(steiner_nodes)

        for edge in steiner_edges:
            # To-Do check this condition...
            if edge[0] in H.edges and edge[2] in H.edges:
                H[edge[0]][edge[2]]['distance'] = -1

        mst_edges = nx.minimum_spanning_edges(H, weight='weight', data=True)
        edges = chain.from_iterable(pairwise(d['path']) for u, v, d in mst_edges)

        selected_edges = []
        for edge in edges:
            selected_edges += [edge]
            selected_edges += [(edge[1], edge[0])]

        tree = graph.edge_subgraph(selected_edges) if selected_edges else graph.subgraph(steiner_nodes)

        return tree

    def bidirected(self, graph):
        biGraph = graph.copy()
        names = nx.get_edge_attributes(graph, 'rname')
        for edge in graph.edges():
            name = names[edge]
            value = 'is-a2' if name == 'is-a' else name
            if not biGraph.has_edge(edge[1], edge[0]):
                biGraph.add_edge(edge[1], edge[0], rname=value)
        return biGraph

    def metric_closure(self, graph, weight='weight'):
        M = nx.Graph()
        Gnodes = set(graph)

        # check for connected graph while processing first node
        all_paths_iter = self.all_pairs_dijkstra(graph, weight=weight)
        u, (distance, path) = next(all_paths_iter)
        if Gnodes - set(distance):
            msg = "G is not a connected graph. metric_closure is not defined."
            raise nx.NetworkXError(msg)
        Gnodes.remove(u)
        for v in Gnodes:
            M.add_edge(u, v, distance=distance[v], path=path[v])

        # first node done -- now process the rest
        for u, (distance, path) in all_paths_iter:
            Gnodes.remove(u)
            for v in Gnodes:
                M.add_edge(u, v, distance=distance[v], path=path[v])
        return M
    
    def all_pairs_dijkstra(self, biGraph, weight='weight'):
        for node in biGraph.nodes():
            g = biGraph.copy()
            attributes = nx.get_edge_attributes(g, 'rname')
            dist = {}
            prev = {}
            last_attribute = {}
            Q = PriorityQueue()

            dist[node] = 0
            prev[node] = [node]
            last_attribute[node] = None

            for n in g.nodes():
                if n != node:
                    dist[n] = float('Inf')
                    prev[n] = []
                Q.insert(dist[n], n)

            while Q.size() > 0:
                p, u = Q.pop()

                for v in g.neighbors(u):
                    p_attribute = last_attribute[u]
                    attribute = attributes[(u, v)]
                    num = 100 if p_attribute == 'is-a' and attribute == 'is-a2' else 0

                    alt = dist[u] + g[u][v].get('weight', 1) + num
                    if alt < dist[v]:
                        dist[v] = alt
                        prev[v] = prev[u] + [v]
                        last_attribute[v] = attribute
                        Q.insert(dist[v], v)
            yield(node, (dist, prev))

    def getRelatedITrees(self, graph, iTree):
        # To-Do : need to consider complicated unionOf 
        return [iTree]

    def getITreeScore(self, selected_set, iTree):
        # add selected relationships
        buf = ['is-a', 'unionOf']
        for element in selected_set:
            if element[2] == 2:
                buf += [element[3] + '.' + element[5]]

        score = 0
        rnames = nx.get_edge_attributes(iTree, 'rname')
        for edge in iTree.edges:
            name = rnames[edge]
            score += 0 if name in buf else 1

        return score

    def drawGraphWithEdges(self, graph, label_name):
        pos = nx.spring_layout(graph)
        labels = nx.get_edge_attributes(graph, label_name)
        nx.draw(graph, pos, with_labels=True, font_weight='bold')
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=labels)
        plt.show()

    def getRoot(self, iTree):
        generator = nx.topological_sort(iTree)
        return next(generator)