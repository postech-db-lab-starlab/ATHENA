import heapq #내부적으로 heapq라이브러리를 사용하기 때문에 import합니다.
class PriorityQueue:
    pq = [] 
    elements = {}
    counter = 0 #이것을 통해서 stable sorting이 가능해집니다!

    def insert(self, priority, value):
        if value in self.elements:
        	#UPDATE하는 경우이면, 기존 priority보다 작을 시에 UPDATE합니다.
            if priority < self.elements[value][0]:
                self.delete(value)
            else:
                return
        entry = [priority, self.counter, value]
        self.counter += 1
        self.elements[value] = entry
        heapq.heappush(self.pq, entry)

    def delete(self, value):
    #지우는 것은 단순히 해당 entry의 value를 None으로 설정합니다.
    #pq에서 지우지 않는 이유는 heap의 특성을 보존하기 위해서입니다.
        entry = self.elements[value]
        entry[-1] = 'z'

    def pop(self):
    #대신 pop을 하면서 deleted된 녀석들을 걸러줍니다.
        while self.pq:
            priority, counter, value = heapq.heappop(self.pq)
            if value != 'z':
                del self.elements[value]
                return priority, value
        raise KeyError('Pop from an empty PriorityQueue')    

    def size(self):
        return len(self.elements)