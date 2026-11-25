/***************************************************************/
/* Program : macros.sas                                        */
/* Purpose : Shared macro library for Northgate Clinical       */
/*           Analytics programs.                               */
/***************************************************************/

%macro clean_dates(ds=, var=date);
    /* Standardise a date variable in place (heuristic stub). */
    %PUT NOTE: clean_dates applied to &ds..&var;
%mend clean_dates;

%macro fmt_report(title);
    /* Apply the standard Northgate report format for &title. */
    TITLE1 "&title";
    FOOTNOTE1 "Northgate Clinical Analytics - fictional sample";
%mend fmt_report;
