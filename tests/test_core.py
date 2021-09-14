
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
		starstar.divide(kwx, b, c, mode='strict')
	assert starstar.divide(kwx, b, c, mode='separate') == [{'a': 'a'}, {'e': 'e'}, {'zzz': 'zzz'}]
	assert starstar.divide(kwx, b, c, mode=None) == [{'a': 'a'}, {'e': 'e'}]


	def b2(a=None, b=None, c=None, **kw):
		return 'b', a, b, c, kw

	def c2(d=None, e=None, f=None, **kw):
		return 'c', d, e, f, kw

	kwx = dict(a='a', e='e', zzz='zzz')
	assert starstar.divide(kwx, b2, c2, mode='strict') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2, varkw=True) == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}]
	assert starstar.divide(kwx, b2, c2, varkw='first') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e'}]
	assert starstar.divide(kwx, b2, c2, varkw=False, mode='ignore') == [{'a': 'a'}, {'e': 'e'}]
	assert starstar.divide(kwx, b2, c2, mode='separate') == [{'a': 'a', 'zzz': 'zzz'}, {'e': 'e', 'zzz': 'zzz'}, {}]




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


def test_defaults():
	@starstar.defaults
	def a(x, y=6, *args, z=7, **kw):
		return x, y, z, kw

	assert a(5) == (5, 6, 7, {})
	assert a(10, 11, z=12) == (10, 11, 12, {})

	assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
	assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
		inspect._empty, 6, inspect._empty, 7, inspect._empty)

	a.update(x=8, z=13)

	assert a() == (8, 6, 13, {})
	assert a(10, 11, z=12) == (10, 11, 12, {})

	assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
	assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
		8, 6, inspect._empty, 13, inspect._empty)

	a.clear()

	assert a(5) == (5, 6, 7, {})
	assert a(10, 11, z=12) == (10, 11, 12, {})

	assert tuple(inspect.signature(a).parameters) == ('x', 'y', 'args', 'z', 'kw')
	assert tuple(p.default for p in inspect.signature(a).parameters.values()) == (
		inspect._empty, 6, inspect._empty, 7, inspect._empty)
