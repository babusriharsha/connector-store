/***************************************************************/
/* Program : old_report.sas                                    */
/* Purpose : Legacy one-off report kept from an earlier        */
/*           Northgate study. Nothing references it any more.  */
/***************************************************************/

DATA oldlib.legacy_report;
    SET oldlib.legacy_extract;
RUN;

PROC PRINT DATA=oldlib.legacy_report;
RUN;
