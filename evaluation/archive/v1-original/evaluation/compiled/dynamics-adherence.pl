:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, markedNote_et(Num, Vel, Dyn)) :- deep_subdict(_event, _{type:"noteon", note:_{number:Num, rawAttack:Vel}, expected:_{dynExplicit:true, dyn:Dyn}}).
match(_event, inAdherence_et(Num, Vel, Dyn)) :- match(_event, markedNote_et(Num, Vel, Dyn)),
	{(((Dyn - 8) =< Vel),(Vel =< (Dyn + 8)))}.
match(_event, inAdherence_et) :- match(_event, inAdherence_et(_, _, _)).
match(_event, unmarkedNote_et) :- deep_subdict(_event, _{type:"noteon", expected:_{dynExplicit:false}}).
match(_event, unmarkedNote_et) :- match(_event, unmarkedNote_et(_)).
match(_event, anyNoteOn_et) :- deep_subdict(_event, _{type:"noteon"}).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Main=((anyNoteOn_et>>star((inAdherence_et\/unmarkedNote_et)));1)).
