:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, notePedal_et) :- deep_subdict(_event, _{type:"noteon", expected:_{pedal:true}}).
match(_event, plainNote_et) :- deep_subdict(_event, _{type:"noteon", expected:_{pedal:false}}).
match(_event, anyNoteOff_et) :- deep_subdict(_event, _{type:"noteoff"}).
match(_event, pedalPress_et) :- deep_subdict(_event, _{type:"controlchange", controller:64, value:127}).
match(_event, pedalRelease_et) :- deep_subdict(_event, _{type:"controlchange", controller:64, value:0}).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Region=(plus(notePedal_et)*(pedalPress_et*star((notePedal_et\/anyNoteOff_et))))),
	(Main=star((((plainNote_et\/anyNoteOff_et)\/pedalRelease_et)\/Region))).
