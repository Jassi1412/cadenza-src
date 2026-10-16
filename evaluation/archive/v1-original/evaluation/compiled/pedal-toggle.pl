:- module(spec, [(trace_expression/2), (match/2)]).
:- use_module(monitor(deep_subdict)).
:- use_module(library(clpr)).
match(_event, pedalPressSpan_et(B, S)) :- deep_subdict(_event, _{type:"controlchange", controller:64, value:127, position:_{beat:B}, expected:_{spanExplicit:true, spanStart:S}}).
match(_event, pedalPress_et) :- match(_event, pedalPressSpan_et(B, S)),
	{(abs((B - S)) =< 0.25)}.
match(_event, pedalReleaseSpan_et(B, E)) :- deep_subdict(_event, _{type:"controlchange", controller:64, value:0, position:_{beat:B}, expected:_{spanExplicit:true, spanEnd:E}}).
match(_event, pedalRelease_et) :- match(_event, pedalReleaseSpan_et(B, E)),
	{(abs((B - E)) =< 0.25)}.
match(_event, anyCC64_et(Ctrl, Val)) :- deep_subdict(_event, _{type:"controlchange", controller:64, value:Val}).
match(_event, anyCC64_et) :- match(_event, anyCC64_et(_, _)).
match(_event, other_et) :- not(match(_event, anyCC64_et)).
match(_event, filler_et) :- deep_subdict(_event, _{type:"noteon"}).
match(_event, filler_et) :- deep_subdict(_event, _{type:"noteoff"}).
match(_event, any_et) :- deep_subdict(_event, _{}).
match(_event, none_et) :- not(match(_event, any_et)).
trace_expression('Main', Main) :- (Toggle=(pedalPress_et*(star(filler_et)*pedalRelease_et))),
	(Main=star((other_et\/Toggle))).
