:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, staccatoOk_et(Num, Vel, D, G)) :- deep_subdict(_event, _{type:"noteon", note:_{number:Num, rawAttack:Vel}, durMs:D, gapMs:G, expected:_{art:"staccato"}}),
	{(D =< (0.75 * G))}.
match(_event, staccatoOk_et) :- match(_event, staccatoOk_et(_, _, _, _)).
match(_event, tenutoOk_et(Num, Vel, D, G)) :- deep_subdict(_event, _{type:"noteon", note:_{number:Num, rawAttack:Vel}, durMs:D, gapMs:G, expected:_{art:"tenuto"}}),
	{(D >= (0.75 * G))}.
match(_event, tenutoOk_et) :- match(_event, tenutoOk_et(_, _, _, _)).
match(_event, legatoOk_et(Num, Vel, D, G)) :- deep_subdict(_event, _{type:"noteon", note:_{number:Num, rawAttack:Vel}, durMs:D, gapMs:G, expected:_{art:"legato"}}),
	{(D >= (0.75 * G))}.
match(_event, legatoOk_et) :- match(_event, legatoOk_et(_, _, _, _)).
match(_event, noMark_et) :- deep_subdict(_event, _{type:"noteon", expected:_{art:null}}).
match(_event, noMark_et) :- match(_event, noMark_et(_)).
match(_event, noGap_et) :- deep_subdict(_event, _{type:"noteon", gapMs:null}).
match(_event, noGap_et) :- match(_event, noGap_et(_)).
match(_event, anyNoteOn_et) :- deep_subdict(_event, _{type:"noteon"}).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Main=((anyNoteOn_et>>star(((((noGap_et\/staccatoOk_et)\/tenutoOk_et)\/legatoOk_et)\/noMark_et)));1)).
