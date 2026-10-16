:- module('deep_subdict', [deep_subdict/2]).

% Tre casi: dizionari, liste, altro.
% Fix Davide (22/01/2020): deep_subdict(V,_{x:1,y:2}) non fallisce sul vuoto.
% Davide (08/06/2020): ordine argomenti allineato a match/2.

deep_subdict(Event, Pattern) :- var(Pattern),!,Pattern=Event.

% pattern vuoto: finito.
deep_subdict(Event, _{}) :- is_dict(Event),!.

% Dizionari.
deep_subdict(Event,Pattern) :-
	% sono dict
	is_dict(Pattern),
	is_dict(Event),
	!,
	% prendi una coppia
	dict_pairs(Pattern, _, [Key-PatternValue|OtherPatternPairs]),
	% trova stessa chiave
	dict_pairs(Event, _, EventPairs),
	member(Key-EventValue, EventPairs),
	% valori compatibili
	deep_subdict(EventValue,PatternValue),
	% rimuovi coppia controllata
	dict_pairs(PatternRest, _, OtherPatternPairs),
	% resto del dict
	deep_subdict(Event,PatternRest).

% Liste di eventi e pattern.
deep_subdict([], []) :- !.
deep_subdict([Event|OtherEvents],[Pattern|OtherPatterns]) :-
	!,
	deep_subdict(Event, Pattern),
	deep_subdict(OtherEvents, OtherPatterns).

% Altro.
deep_subdict(X, X).
