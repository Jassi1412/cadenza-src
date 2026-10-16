:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, soloNote_et) :- deep_subdict(_event, _{type:"noteon", expected:_{chordMates:[]}}).
match(_event, soloNote_et) :- match(_event, soloNote_et(_)).
match(_event, chordNote_et(Cid, Ts)) :- deep_subdict(_event, _{type:"noteon", expected:_{chordId:Cid, chordMates:_}, timestamp:Ts}).
match(_event, anyNoteOn_et) :- deep_subdict(_event, _{type:"noteon"}).
match(_event, mateOf_et(C, T1)) :- match(_event, chordNote_et(C, T2)),
	{(abs((T2 - T1)) < 30)}.
match(_event, mateOf_et) :- match(_event, mateOf_et(_, _)).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Chord=var(c, var(t1, (chordNote_et(var(c), var(t1))*(mateOf_et(var(c), var(t1))*star(mateOf_et(var(c), var(t1)))))))),
	(Main=((anyNoteOn_et>>star((soloNote_et\/Chord)));1)).
