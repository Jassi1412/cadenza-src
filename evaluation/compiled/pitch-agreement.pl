:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, noteOn_et(Num, Dist)) :- deep_subdict(_event, _{type:"noteon", note:_{number:Num}, expected:_{pitchDist:Dist}}).
match(_event, inScore_et(Num)) :- match(_event, noteOn_et(Num, Dist)),
	{((Dist >= 0),(Dist =< 0))}.
match(_event, inScore_et) :- match(_event, inScore_et(_)).
match(_event, unmatchedNote_et) :- match(_event, noteOn_et(_, null)).
match(_event, anyNoteOn_et) :- deep_subdict(_event, _{type:"noteon"}).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Main=((anyNoteOn_et>>star((unmatchedNote_et\/inScore_et)));1)).
