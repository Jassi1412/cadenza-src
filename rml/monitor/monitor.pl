:- use_module(library(http/json)).
:- use_module(monitor(trace_expressions_semantics)).
:- initialization(main).

%% Argomenti richiesti: specFile, traceFile.
%% Opzioni: --silent (niente output su transizioni), --verbose (eventi+stati),
%%          --reject (accetta tracce non valide).
%% Flag gestiti con compilazione condizionale (Davide):
%%   :- if(:Goal) ... :- elif(:Goal) ... :- else ... :- endif
%%   vedi https://www.swi-prolog.org/pldoc/man?section=conditionalcompilation
%% Flag debug da aggiungere per unire monitor.pl e monitor_debug.pl.
%% Predicati per gestire opzioni.

option(Opt) :-
    current_prolog_flag(argv, [_, _ | Arguments]),
    member(Opt, Arguments).

reject :- fail.
:- if(option('--reject')).
reject.
:- endif.

:- discontiguous log/1,logln/1.
log(_):-fail.
logln(_):-fail.
:- if(option('--silent')).
log(_).
logln(_).
:- else.
log(X) :- write(X).
logln(X) :- writeln(X).
:- endif.

write_info(_,_,_) :- fail.
:- if(option('--verbose')).
write_info(EventId,Event,NewTraceExp) :- log('matched event #'), log(EventId), log(': '), logln(Event), logln(NewTraceExp).
:- else.
write_info(EventId,Event,_) :- log('matched event #'), log(EventId), log(': '), logln(Event).
:- endif.

main :-
    current_prolog_flag(argv, [SpecFile, TraceFile | _]), %!, %% argomenti richiesti
    load_spec(SpecFile,TraceExp),
    read_trace(TraceFile, TraceStream),
    (verify(TraceStream, TraceExp) ->
	 (writeln('Execution terminated correctly'), Exit=0); (writeln('Trace did not match specification'), Exit=1)),
    close(TraceStream),
    halt(Exit).

main :-
	writeln('expected args: <spec file> <trace file>'),
	halt(1).
	
file_not_found(Fname) :- write('File not found: '), writeln(Fname), halt(1).

load_spec(SpecFile,TraceExp) :-
    catch(
	(use_module(SpecFile), trace_expression(_, TraceExp)),
	error(existence_error(_,Fname),_),
	file_not_found(Fname)
    ).

read_trace(TraceFile, TraceStream) :-
    catch(
    	open(TraceFile, read, TraceStream),
    	Err,
    	(Err=error(existence_error(_,Fname),_)->
	     file_not_found(Fname); (writeln('Illegal JSON object'), halt(1))
	)
    ).

%% verify(TraceStream, TraceExp, EventId) :-
%%   at_end_of_stream(TraceStream) -> verify_end(TraceExp) ; verify_events(TraceStream, TraceExp, EventId).

% verifica se fine traccia e' permessa
verify_end(TraceExp) :- may_halt(TraceExp) ->
	true ;
	(writeln('Unmatched end of trace'), fail).

% verifica un evento e procede ricorsivamente
%%% Nota: json_read_dict lancia syntax_error se EOF prima di at_end_of_stream;
%%% workaround con end_of_file(empty{}) non valido: aggiungerebbe evento.
%%% Soluzione: catturare eccezione e chiamare verify_end.
%%% Versione commentata di verify e' inutile; 'verify_events' rinominata 'verify'.
%%% Formato output: log(Event) invece di log(Fields) da dict_pairs.
verify(TraceStream, TraceExp) :-
    catch(
	(reject -> \+ verify(TraceStream, TraceExp, 1); verify(TraceStream, TraceExp, 1)),
        error(syntax_error(json(illegal_json)),_),
	(writeln('Illegal JSON syntax'),halt(1))).

%% Davide 25/09/2024: json_read_dict non lancia su EOF.
%% Rimosso catch, predicato tail recursive, evita stack overflow.
verify(TraceStream, TraceExp, EventId) :-
    json_read_dict(TraceStream, Event,[end_of_file(@(eof))]),
    (Event == @(eof) -> %% EOF raggiunto
	 verify_end(TraceExp)
    ;
    (next(TraceExp, Event, NewTraceExp)
    -> (write_info(EventId,Event,NewTraceExp), NewEventId is EventId+1, verify(TraceStream, NewTraceExp, NewEventId))
     ;  (log('unmatched event #'), log(EventId), log(': '), logln(Event), fail)
    )).



