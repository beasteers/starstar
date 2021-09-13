
import pytest
import inspect
import starstar


def test_divide():
	def b(a=None, b=None, c=None):
		return 'b', a, b, c

	def c(d=None, e=None, f=None, c=None):
		return 'c', d, e, f, c

	kw = dict(a='a', e='e')
	assert starstar.divide(kw, b, c) == [{'a': 'a'}, {'e': 'e'}]

	kw = dict(a='a', e='e', c='c')
	assert starstar.divide(kw, b, c) == [{'a': 'a', 'c': 'c'}, {'e': 'e', 'c': 'c'}]

	kwx = dict(a='a', e='e', zzz='zzz')
	with pytest.raises(TypeError):
		starstar.divide(kwx, b, c, overflow='strict')
	assert starstar.divide(kwx, b, c, overflow='separate') == [{'a': 'a'}, {'e': 'e'}, {'zzz': 'zzz'}]
	assert starstar.divide(kwx, b, c, overflow=None) == [{'a': 'a'}, {'e': 'e'}]


	def b2(a=None, b=None, c=None, **kw):
		return 'b', a, b, c, kw

	def c2(d=None, e=None, f=None, **kw):
		return 'c', d, e, f, kw

	kwx = dict(a='a', e='e', zzz='zzz')
	assert starstar.divide(kwx, b2, c2, overflow='strict') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2, overflow_first=False) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2, overflow_first=True) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e'}]
	assert starstar.divide(kwx, b2, c2, overflow='separate') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}, {}]




def test_core():
	def b(a=None, b=None, c=None):
		return 'b', a, b, c

	def c(d=None, e=None, f=None):
		return 'c', d, e, f
	
	@starstar.traceto(b, c)
	def a(aaa=None, **kw):
		kw_b, kw_c = starstar.divide(kw, b, c)
		return b(**kw_b), c(**kw_c)

	a_names = {'aaa', 'a', 'b', 'c', 'd', 'e', 'f'}
	assert set(a.__signature__.parameters) == a_names

	a_return = ('b', 'a', 'b', 'c'), ('c', 'd', 'e', 'f')
	assert a(**{x: x for x in a_names}) == a_return


	def x(x=None, y=None, z=None):
		return 'x', x, y, z

	@starstar.traceto(a, x)
	def asdf(**kw):
		kw_a, kw_x = starstar.divide(kw, (a, b, c), x)
		return a(**kw_a), x(**kw_x)

	asdf_names = a_names | {'x', 'y', 'z'}
	assert set(asdf.__signature__.parameters) == asdf_names

	asdf_return = a_return, ('x', 'x', 'y', 'z')
	assert asdf(**{x: x for x in asdf_names}) == asdf_return

	@starstar.traceto(a, x)
	def asdf2(**kw):
		kw_a, kw_x = starstar.divide(kw, a, x)
		return a(**kw_a), x(**kw_x)

	assert set(asdf2.__signature__.parameters) == asdf_names
	assert asdf2(**{x: x for x in asdf_names}) == asdf_return


def test_wraps():
	def a(x, y, *aaa, z, **kwaaa):
		pass

	@starstar.wraps(a)
	def asdf(q, *a, **kw):
		pass

	assert tuple(inspect.signature(asdf).parameters) == ('q', 'x', 'y', 'aaa', 'z', 'kwaaa')