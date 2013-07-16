window.$ = django.jQuery;
$(function(){
    $('td.field-field_type select').live('change', function() {

        $(this).parent()
            .siblings('.field-choices, .field-autocomplete, .field-placeholder_text')
            .children('input')
            .attr('disabled', 'disabled');

        switch(parseInt($(this).val())) {

            case 1:
            $(this).parent()
                .siblings('.field-autocomplete, .field-placeholder_text')
                .children('input')
                .removeAttr('disabled');
            break;

            case 4:
            case 5:
            case 6:
            case 7:
            case 8:
            $(this).parent()
                .siblings('.field-choices')
                .children('input')
                .removeAttr('disabled');

            this
            break;

        }
    });

    $('td.field-field_type select').trigger('change');

});
