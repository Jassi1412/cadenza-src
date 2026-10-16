:- use_module(library(http/json)).
:- use_module(monitor(trace_expressions_semantics)).
:- initialization(main).

main :-
    current_prolog_flag(argv, [TraceFile | Rest]),
    Rest \== [],
    pair_up(Rest, Pairs),
    open_trace(TraceFile, Stream),
    forall(member(Name-Spec, Pairs), run_one(Name, Spec, Stream)),
    close(Stream),
    halt(0).

main :-
    format("batch.pl: attesi <traccia.jsonl> poi coppie <nome> <specifica.pl>~n"),
    halt(2).

pair_up([], []).
pair_up([Name, Spec | Rest], [Name-Spec | Pairs]) :-
    pair_up(Rest, Pairs).

open_trace(TraceFile, Stream) :-
    catch(open(TraceFile, read, Stream), Error, trace_error(2, Error)).

%% Carica spec, verifica, riporta exit, scarica spec.
run_one(Name, SpecFile, Stream) :-
    seek(Stream, 0, bof, _),
    (   catch(( load_spec(SpecFile, TraceExp), verify(Stream, TraceExp) -> Exit = 0 ; Exit = 1 ),
              Error, ( print_message(error, Error), Exit = 2 ))
    ->  true
    ;   Exit = 2
    ),
    unload_spec(SpecFile),
    format("~w ~w~n", [Name, Exit]).

load_spec(SpecFile, TraceExp) :-
    use_module(SpecFile),
    trace_expression(_, TraceExp).

unload_spec(SpecFile) :-
    catch(unload_file(SpecFile), _, true).

trace_error(Exit, _) :- format("~w ~w~n", ['monitor', Exit]).

verify_end(TraceExp) :- may_halt(TraceExp) -> true ; fail.

verify(TraceStream, TraceExp) :-
    catch(
        ( reject -> \+ verify(TraceStream, TraceExp, 1) ; verify(TraceStream, TraceExp, 1) ),
        error(syntax_error(json(illegal_json)), _),
        fail).

verify(TraceStream, TraceExp, EventId) :-
    json_read_dict(TraceStream, Event, [end_of_file(@(eof))]),
    (   Event == @(eof) -> verify_end(TraceExp)
    ;   next(TraceExp, Event, NewTraceExp)
    ->  NextEventId is EventId + 1,
        verify(TraceStream, NewTraceExp, NextEventId)
    ;   fail
    ).

%% Senza --reject, esecuzione non conforme = fallimento normale.
reject :- fail.
