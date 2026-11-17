"""Excel más rápido: openpyxl buscaba cada formato (letra, relleno, borde…) calculando su huella completa en
cada celda. Como Ctrl-P reutiliza los mismos objetos de formato, se recuerda el lugar de cada objeto ya visto.
El archivo que sale es idéntico."""
from openpyxl.utils.indexed_list import IndexedList

if not getattr(IndexedList, "_ctrlp_rapido", False):
    _add = IndexedList.add

    def _add_rapido(self, value):
        c = self.__dict__.get("_por_id")
        if c is None:
            c = self.__dict__["_por_id"] = {}
        k = id(value)
        hit = c.get(k)
        if hit is not None and hit[0] is value and self.clean:
            return hit[1]
        i = _add(self, value)
        c[k] = (value, i)           # se guarda el objeto: su id no se reutiliza mientras viva
        return i
    IndexedList.add = _add_rapido
    IndexedList._ctrlp_rapido = True
