# Development dataset examples

Stage validation varies by record; this is not a benchmark release.

## astropy__astropy-12907.source.v1.f4a4dd2ca5

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied astropy/astropy repository. Adjust Astropy modeling's separability matrix calculation for CompoundModels.

I’m not sure what the separability matrix should report for nested CompoundModels. What behavior should it have? Please preserve existing behavior outside the requested changes.

**U1**

For nested CompoundModels, compute separability correctly while preserving independent input/output relationships. Keep existing behavior outside this change.

Update the supplied astropy/astropy repository to meet these requirements:
- Compute separability correctly for nested CompoundModels, preserving independent input/output relationships in nested compositions.
Preserve unrelated existing behavior.

## astropy__astropy-14365.source.v1.71e2eb9e3a

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied astropy/astropy repository. Astropy’s `ascii.qdp` reader parses QDP commands while loading a file into a `Table`.

I’ll work on QDP command parsing while loading files into a Table, preserving behavior outside the requested changes. Which command casing should the reader accept?

**U1**

Please recognize QDP commands case-insensitively, including lowercase `read serr 1 2`, and load the data into a Table with errors instead of raising an unrecognized-line error.

Update the supplied astropy/astropy repository to meet these requirements:
- When reading a QDP file, recognize commands case-insensitively, including lowercase `read serr 1 2`, and read the data into a `Table` with errors rather than raising an unrecognized-line error.
Preserve unrelated existing behavior.

## astropy__astropy-14995.source.v1.9663ce03c1

Class: `mixed`; updates: `addition -> clarification`.

**U0**

Work in the supplied astropy/astropy repository. The NDDataRef arithmetic mask propagation behavior in astropy 5.3 is under discussion, including operations where masks may be present on the operands.

Please preserve existing behavior outside the changes under discussion. If only one arithmetic operand has a mask, what should happen to the output mask?

**U1**

Also, when both arithmetic operands have masks, propagate them using the configured mask handler. The question about only one operand having a mask remains open.

**U2**

For an NDDataRef with a mask combined arithmetically with a scalar or other operand without a mask, preserve the existing mask in the output and do not raise an error. When both operands have masks, continue to propagate them using the configured mask handler, and preserve unrelated existing behavior.

Update the supplied astropy/astropy repository to meet these requirements:
- When an NDDataRef with a mask is combined arithmetically with a scalar or other operand without a mask, preserve the existing mask in the output without raising an error.
- When both arithmetic operands have masks, propagate them using the configured mask handler.
Preserve unrelated existing behavior.

## astropy__astropy-6938.source.v1.f291d17ad4

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied astropy/astropy repository. This concerns Astropy's `io.fits` record-writing path, which formats floating-point values for FITS output. The desired exponent handling is left open for clarification.

Please update Astropy’s FITS record-writing path to format floating-point values. Preserve existing behavior outside the requested changes. Should fields with a `D` format use `D` instead of `E` as the exponent separator?

**U1**

Use `D` instead of `E` for exponent separators when writing floating-point fields whose format contains `D`. Preserve existing behavior outside this change.

Update the supplied astropy/astropy repository to meet these requirements:
- When writing floating-point fields whose format contains `D`, replace `E` exponent separators with `D` in the output.
Preserve unrelated existing behavior.

## astropy__astropy-7746.source.v1.edecbc37f3

Class: `clarification`; updates: `clarification -> clarification`.

**U0**

Work in the supplied astropy/astropy repository. Astropy WCS coordinate transformations.

I’m looking into WCS coordinate transformations and want to preserve existing behavior outside the changes we agree on. Should empty list inputs be covered? Should empty array inputs be covered?

**U1**

Please include empty lists as WCS coordinate inputs. Transformations should return the corresponding empty lists or arrays without failing. Should empty array inputs be covered too?

**U2**

Please also include empty arrays as WCS coordinate inputs. Transformations should return the corresponding empty lists or arrays without failing.

Update the supplied astropy/astropy repository to meet these requirements:
- WCS transformations accept empty lists as coordinate inputs and return corresponding empty lists or arrays without failing.
- WCS transformations accept empty arrays as coordinate inputs and return corresponding empty lists or arrays without failing.
Preserve unrelated existing behavior.

## django__django-10924.source.v1.7771b44fbd

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. Django's FilePathField lets a model specify a filesystem path, and migrations record field configuration. The request concerns how the field's path may be supplied across environments.

Please preserve existing behavior outside the changes requested. Should `FilePathField.path` accept a callable, and should migrations preserve it so the path can be resolved in the environment where they run?

**U1**

Clarification: `FilePathField.path` must accept a callable, and migrations must preserve that callable so the path can be resolved in the environment where they run.

Update the supplied django/django repository to meet these requirements:
- FilePathField.path must accept a callable, and migrations must preserve that callable so the path can be resolved in the environment where migrations are run.
Preserve unrelated existing behavior.

## django__django-11039.source.v1.3fa45707e2

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. This task concerns Django's sqlmigrate command and whether generated migration SQL is wrapped in transaction statements.
Preserve existing behavior outside the changes currently requested.

Should sqlmigrate’s outer transaction statements for an atomic migration depend on whether the database supports rolling back DDL?

**U1**

For an atomic migration, include outer BEGIN/COMMIT statements in sqlmigrate output only if the database supports rolling back DDL (`connection.features.can_rollback_ddl`).

Update the supplied django/django repository to meet these requirements:
- For an atomic migration, sqlmigrate should wrap its output in outer BEGIN/COMMIT statements only when the database supports rolling back DDL (connection.features.can_rollback_ddl).
Preserve unrelated existing behavior.

## django__django-11049.source.v1.637b9c3730

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. Django’s DurationField accepts duration strings and reports an expected format when input is invalid. Review the format shown in that error message.
Preserve existing behavior outside the changes currently requested.

Please review the expected format shown in the error message for invalid DurationField input. What should that format be?

**U1**

For invalid DurationField input, show the expected format as `[DD] [[HH:]MM:]ss[.uuuuuu]`, with seconds mandatory and minutes and hours optional as described.

Update the supplied django/django repository to meet these requirements:
- For invalid DurationField input, show the expected format as `[DD] [[HH:]MM:]ss[.uuuuuu]`, with seconds mandatory and minutes and hours optional as described.
Preserve unrelated existing behavior.

## django__django-11742.source.v1.5df1f25386

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django fields can define both Field.max_length and Field.choices. Overlong choice values can go unnoticed until a record using them is saved. We need to address length validation for these choices, including how to handle unused legacy entries.
Preserve existing behavior outside the changes currently requested.

I'm unsure whether length validation should apply only to the choice selected for a record, allowing longer unused entries, or to every value declared in Field.choices.

**U1**

Validate the selected choice against Field.max_length when saving a record, while allowing longer unused values to remain in Field.choices.

**U2**

Replace that selected-choice-only policy: check that Field.max_length is large enough to fit the longest value in Field.choices, including unused entries.

Update the supplied django/django repository to meet these requirements:
- Check that Field.max_length is large enough to fit the longest value in Field.choices.
Preserve unrelated existing behavior.

## django__django-11848.source.v1.f172266671

Class: `clarification`; updates: `clarification -> clarification`.

**U0**

Work in the supplied django/django repository. When Django parses an HTTP date in RFC 850 format with a two-digit year, the current fixed year mapping can give an incorrect result. Please update the parsing behavior.
Preserve existing behavior outside the changes currently requested.

How should RFC 850 dates with two-digit years be interpreted when the fixed year mapping may produce an incorrect result?

**U1**

Please interpret RFC 850 two-digit years relative to the current year rather than using a fixed century mapping.

**U2**

More specifically, compare the parsed year with the current year. If it is more than 50 years in the future, use the most recent past year with the same final two digits. Do not use the fixed 00–69-to-2000–2069 and 70–99-to-1970–1999 mapping.

Update the supplied django/django repository to meet these requirements:
- When parsing an RFC 850 date with a two-digit year, compare the parsed year with the current year; if it is more than 50 years in the future, interpret it as the most recent past year with the same final two digits.
- Do not use the fixed mapping of 00–69 to 2000–2069 and 70–99 to 1970–1999 to interpret these years.
Preserve unrelated existing behavior.

## django__django-11999.source.v1.1da25081a1

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied django/django repository. Django models generate display methods for fields that have choices. In a model’s field and method definitions,
Preserve existing behavior outside the changes currently requested.

For fields with choices, keep Django’s generated `get_FIELD_display()` method authoritative if the model defines a method with the same name.

**U1**

Change that requirement: allow a model-defined `get_FIELD_display()` method to override Django’s generated method for fields with choices.

Update the supplied django/django repository to meet these requirements:
- Allow a model-defined get_FIELD_display() method to override the generated method for a field with choices.
Preserve unrelated existing behavior.

## django__django-12184.source.v1.a24ee5a734

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. Django URL resolution passes captured URL arguments to the matched view. An optional named capture can be omitted from the requested URL, and the view may define a default for a corresponding parameter.
Preserve existing behavior outside the changes currently requested.

When a URL omits an optional named capture, should Django leave out that argument so the view’s default parameter value applies?

**U1**

Yes: when a URL pattern has an optional named capture and the requested URL omits it, dispatch to a view with a corresponding defaulted parameter without passing an unexpected extra positional argument.

Update the supplied django/django repository to meet these requirements:
- When a URL pattern has an optional named capture and the requested URL omits it, dispatch to a view with a corresponding defaulted parameter without passing an unexpected extra positional argument.
Preserve unrelated existing behavior.

## django__django-12284.source.v1.0b82715abf

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. Django generates a `get_FOO_display()` method for model fields with choices. In an abstract base model and a child model that redeclares the choices field, the generated method currently returns the raw value for a choice added by the child.
Preserve existing behavior outside the changes currently requested.

For a choice added by the child model, should `get_FOO_display()` return the label configured on the child field?

**U1**

Yes. When a child model overrides an inherited choices field and adds choices, its generated display method must return the configured label for those added choices.

Update the supplied django/django repository to meet these requirements:
- When a child model overrides an inherited choices field and adds choices, its generated display method must return the configured label for those added choices.
Preserve unrelated existing behavior.

## django__django-12286.source.v1.2b87170dfc

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. In Django 3.0.2, setting LANGUAGE_CODE to "de-at" produces translation.E004 when LANGUAGES contains "de" but not "de-at". The error says LANGUAGE_CODE is not in LANGUAGES. Please address this system-check behavior.
Preserve existing behavior outside the changes currently requested.

I'm unsure whether translation.E004 should accept a LANGUAGE_CODE sublanguage missing from LANGUAGES when its base language is available there.

**U1**

Do not raise translation.E004 when LANGUAGE_CODE specifies a sublanguage whose base language is available in LANGUAGES.

Update the supplied django/django repository to meet these requirements:
- Do not raise translation.E004 when LANGUAGE_CODE specifies a sublanguage whose base language is available in LANGUAGES.
Preserve unrelated existing behavior.

## django__django-12453.source.v1.a7e4d82db5

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied django/django repository. In Django, `TransactionTestCase` with `serialized_rollback = True` restores database contents by deserializing a snapshot. When a restored object references another object that has not yet been saved, the restore can fail with an integrity error. What behavior should restoration use to handle this ordering case?
Preserve existing behavior outside the changes currently requested.

For serialized rollback restoration, should the snapshot be deserialized inside a transaction on the connection’s database alias?

**U1**

Please deserialize the serialized database contents within a transaction using the connection’s database alias, so restoration can handle objects saved before the objects their foreign keys reference.

Update the supplied django/django repository to meet these requirements:
- Deserialize the serialized database contents within a transaction using the connection's database alias, so restoration can handle objects saved before the objects their foreign keys reference.
Preserve unrelated existing behavior.

## django__django-12497.source.v1.dcad883af3

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's many-to-many validation produces a recursive-relationship hint when an intermediary model has more than two ForeignKeys and through_fields is unset. The hint currently suggests ForeignKey with many-to-many options, and its guidance about symmetry needs review.
Preserve existing behavior outside the changes currently requested.

Please review the suggested field declaration in this hint. Should the corrected declaration explicitly require symmetrical=False to clarify directionality, or omit that requirement in line with current Django support?

**U1**

For the recursive-relationship hint when an intermediary model has more than two ForeignKeys and through_fields is unset, recommend ManyToManyField and retain symmetrical=False as required guidance to make directionality explicit.

**U2**

Revise my earlier symmetry guidance: omit the outdated symmetrical=False requirement from that hint. Keep the correction from ForeignKey to ManyToManyField.

Update the supplied django/django repository to meet these requirements:
- When a many-to-many intermediary model has more than two ForeignKeys and through_fields is unset, correct the recursive-relationship error hint to recommend ManyToManyField instead of ForeignKey and omit the outdated symmetrical=False requirement.
Preserve unrelated existing behavior.

## django__django-12589.source.v1.69d73b6421

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's ORM encounters an ambiguous column reference when a query groups through values() over a correlated Subquery annotation named status, while joined tables also contain status columns. The query also contains Count annotations and joins introduced by related-object filtering.
Preserve existing behavior outside the changes currently requested.

Please investigate this alias collision. Should the ORM reject the query with a clear validation error or support it by generating unambiguous GROUP BY SQL?

**U1**

Reject values()-based aggregation over a correlated Subquery annotation when its alias matches column names in joined tables. Raise an explicit validation error before executing ambiguous SQL.

**U2**

Change the policy from rejecting these queries to supporting them: generate unambiguous GROUP BY clauses for values()-based aggregation over a correlated Subquery annotation whose alias matches column names in joined tables, preserving the intended grouping and allowing the query to evaluate successfully.

Update the supplied django/django repository to meet these requirements:
- Generate unambiguous GROUP BY clauses when aggregating over a correlated Subquery annotation through values() and its alias matches column names in joined tables, preserving the intended grouping and allowing the query to evaluate successfully.
Preserve unrelated existing behavior.

## django__django-12908.source.v1.5777f1a0b9

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, distinct() can silently have no effect after QuerySet.union(). The reported case combines two annotated querysets, then calls order_by('name').distinct('name'). The handling of this chained operation needs to be explicit.
Preserve existing behavior outside the changes currently requested.

Please investigate this chaining behavior. I'm unsure whether distinct() after union() should perform the requested deduplication or raise an error.

**U1**

Support distinct() after union() so that the requested deduplication takes effect, including when distinct fields are supplied.

**U2**

Change the requirement from supporting deduplication to raising an error when distinct() is called on a union queryset, including when distinct fields are supplied. It must not silently have no effect.

Update the supplied django/django repository to meet these requirements:
- Calling distinct() on a union queryset must raise an error instead of silently having no effect, including when distinct fields are supplied.
Preserve unrelated existing behavior.

## django__django-12915.source.v1.16d640644a

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In django/django, static-file requests through ASGIStaticFilesHandler fail with TypeError: 'NoneType' object is not callable when the async response path reaches the middleware chain. Investigate the handler’s response path and establish how these requests should be handled.
Preserve existing behavior outside the changes currently requested.

I'm unsure whether ASGIStaticFilesHandler should serve static-file requests asynchronously or explicitly reject them with a clear unsupported-operation error. Please assess which behavior is appropriate.

**U1**

Have ASGIStaticFilesHandler explicitly reject matching static-file requests with a clear unsupported-operation error, since static assets will be served separately.

**U2**

Change the earlier rejection policy to support asynchronous static-file requests. Add get_response_async to StaticFilesHandlerMixin so ASGIStaticFilesHandler can handle those requests without the reported NoneType middleware-chain failure.

Update the supplied django/django repository to meet these requirements:
- Add get_response_async to StaticFilesHandlerMixin so ASGIStaticFilesHandler can handle static-file requests asynchronously without the reported NoneType middleware-chain failure.
Preserve unrelated existing behavior.

## django__django-12983.clarification_revision.v6.716d63e7

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Update `django.utils.text.slugify` in Django. Preserve existing normalization except where the requested underscore or boundary rules change it, and remove dashes from both ends of the resulting slug. Should underscores be removed everywhere, including internally, or only at both ends while preserving internal underscores? For the boundary-only option, include mixed boundaries of dashes, underscores, and whitespace.

**U1**

For `django.utils.text.slugify`, remove every underscore from the resulting slug, including internal underscores. Keep the existing requirements to remove dashes from both ends and preserve other existing normalization except where the requested underscore or boundary rules change it.

**U2**

Revise the underscore rule for `django.utils.text.slugify`: withdraw the requirement to remove every underscore, including internal ones. Instead, remove underscores at both ends of the resulting slug, including mixed boundaries of dashes, underscores, and whitespace, while preserving underscores inside the slug. Keep the existing requirement to remove dashes from both ends and preserve all other existing normalization behavior.

Update django.utils.text.slugify so the normalized result has no dashes or underscores at either end, including mixed boundaries of dashes, underscores and whitespace. Preserve underscores inside the slug and all other existing normalization behavior.

## django__django-13028.source.v1.f8ca60a317

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django queryset validation encounters model instances with an ordinary Boolean field named filterable. Passing an instance whose field is False as the right-hand side of a foreign-key filter currently raises NotSupportedError.
Preserve existing behavior outside the changes currently requested.

Please investigate whether an ordinary model field named filterable should control whether the instance can be used in queryset filters. I'm unsure whether False should disallow that use or whether filtering should accept the instance regardless of the field's value.

**U1**

Treat filterable=False as an explicit opt-out: intentionally reject right-hand-side model instances whose filterable attribute is False.

**U2**

Replace that rejection policy with allowing queryset filters to use a right-hand-side model instance whose ordinary filterable attribute is False, without incorrectly raising NotSupportedError.

Update the supplied django/django repository to meet these requirements:
- Allow queryset filtering with a right-hand-side model instance whose ordinary filterable attribute is False, without incorrectly raising NotSupportedError.
Preserve unrelated existing behavior.

## django__django-13033.source.v1.43e59c94ff

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, ordering through a related model by a self-referencing foreign key's _id field can unexpectedly use the related model's Meta.ordering and introduce an extra self-join. Both unprefixed and minus-prefixed ordering paths are affected. Investigate how these explicit column paths are handled so we can choose an appropriate handling policy.
Preserve existing behavior outside the changes currently requested.

Please investigate whether these self-referencing foreign-key _id ordering paths should be rejected to prevent misleading results or supported by ordering directly on the column in the requested direction. I'm unsure which policy is appropriate.

**U1**

Reject order_by() paths targeting self-referencing foreign-key _id fields, including paths through related models and either sort direction. Raise a clear error so callers cannot silently receive misleading ordering.

**U2**

Replace the earlier rejection policy with support for these order_by() paths, including paths through related models. Order directly by the stored foreign-key column without an unnecessary self-join, using ascending order for an unprefixed path and descending order for a minus-prefixed path, independently of the related model's Meta.ordering.

Update the supplied django/django repository to meet these requirements:
- When order_by() targets a self-referencing foreign key's _id field, including through related-model paths, order directly by the stored foreign-key column without an unnecessary self-join. Honor ascending ordering for an unprefixed path and descending ordering for a minus-prefixed path, independently of the related model's Meta.ordering.
Preserve unrelated existing behavior.

## django__django-13158.source.v1.8674886757

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, calling QuerySet.none() on a combined queryset can still return matching objects. This affects an optional ModelMultipleChoiceField backed by a union() queryset: submitting the form without selecting publications can associate every matching publication. The handling policy for none() on combined querysets needs to be decided.
Preserve existing behavior outside the changes currently requested.

Please investigate the behavior of none() on combined querysets. I’m unsure whether it should explicitly reject the operation or return an empty queryset.

**U1**

Explicitly reject calls to QuerySet.none() on combined querysets with an exception.

**U2**

Change the policy from raising an exception to making QuerySet.none() return no results for combined querysets, including union() querysets, so an empty submission of an optional ModelMultipleChoiceField using such a queryset adds no objects.

Update the supplied django/django repository to meet these requirements:
- Make QuerySet.none() return no results for combined querysets, including union() querysets, so an empty submission of an optional ModelMultipleChoiceField using such a queryset adds no objects.
Preserve unrelated existing behavior.

## django__django-13220.source.v1.8069f27c2a

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied django/django repository. Django's django.core.exceptions.ValidationError instances currently compare unequal even when created with identical messages, which makes assertions in tests cumbersome.
Preserve existing behavior outside the changes currently requested.

Add ValidationError.__eq__ so that identically created ValidationError instances with identical messages compare equal.

**U1**

Also make ValidationError comparison independent of the order of errors within a field or within non_field_errors.

Update the supplied django/django repository to meet these requirements:
- Add ValidationError.__eq__ to support comparing ValidationErrors, making identically created instances with identical messages compare equal.
- Make ValidationError comparison independent of the order of errors within a field or within non_field_errors.
Preserve unrelated existing behavior.

## django__django-13230.source.v1.848fb7bc89

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's syndication feed parser explicitly recognizes comments, but supplying them through syndication.views currently requires item_extra_kwargs. We are deciding how the view should expose this item metadata.
Preserve existing behavior outside the changes currently requested.

Please investigate how comments metadata is handled in syndication.views. Should it remain available only through item_extra_kwargs, or should the view support item_comments directly?

**U1**

Keep comments metadata available only through item_extra_kwargs; do not add direct item_comments support in syndication.views.

**U2**

Replace the earlier restriction with direct item_comments support: pass a comments argument to feed.add_item() in syndication.views so item_comments can be defined without using item_extra_kwargs.

Update the supplied django/django repository to meet these requirements:
- Pass a comments argument to feed.add_item() in syndication.views so item_comments can be defined directly without using item_extra_kwargs.
Preserve unrelated existing behavior.

## django__django-13315.source.v1.8693ee7922

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django ForeignKey form fields can display repeated options when limit_choices_to is a Q object involving a join. Investigate how these filters are handled when constructing form choices.
Preserve existing behavior outside the changes currently requested.

Please assess whether these join-based Q filters should be rejected or supported with each option appearing only once; I'm unsure which behavior is appropriate.

**U1**

Reject ForeignKey limit_choices_to Q objects involving joins with a clear error when constructing the form field, preventing potentially repeated choices.

**U2**

Replace the rejection policy with support for these filters: ForeignKey form fields must not render duplicate options when limit_choices_to uses a Q object involving a join.

Update the supplied django/django repository to meet these requirements:
- Ensure ForeignKey form fields do not render duplicate options when limit_choices_to uses a Q object involving a join.
Preserve unrelated existing behavior.

## django__django-13401.source.v1.5e41a94bac

Class: `cumulative`; updates: `addition -> addition`.

**U0**

Work in the supplied django/django repository. In Django, an abstract model A defines an IntegerField named myfield, and concrete models B and C inherit it. B._meta.get_field('myfield') and C._meta.get_field('myfield') currently compare equal because they share a creation_counter.
Preserve existing behavior outside the changes currently requested.

Adjust field equality so that fields belonging to different models compare unequal, including fields inherited from the same abstract model.

**U1**

Also adjust field hashing to remain consistent with model-sensitive field equality.

**U2**

Also adjust field ordering to match model-sensitive equality. Keep creation_counter as the primary ordering key so that fields unaffected by the equality collision retain their order.

Update the supplied django/django repository to meet these requirements:
- Adjust field equality so that fields belonging to different models compare unequal, including fields inherited from the same abstract model.
- Adjust field hashing to remain consistent with model-sensitive field equality.
- Adjust field ordering to match model-sensitive equality, retaining creation_counter as the primary ordering key so that fields unaffected by the equality collision retain their order.
Preserve unrelated existing behavior.

## django__django-13448.source.v1.d562bb9671

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django 3.1, running ./manage.py test with TEST.MIGRATE set to False crashes during test database setup. Database serialization queries django_admin_log, which does not exist, and the traceback ends with a cursor error. Investigate how setup should handle this migration-disabled configuration.
Preserve existing behavior outside the changes currently requested.

Investigate whether test database setup should explicitly reject TEST.MIGRATE=False with a clear configuration error or support running tests with migrations skipped.

**U1**

Reject TEST.MIGRATE=False during test database setup with a clear configuration error.

**U2**

Replace the earlier rejection policy with support for TEST.MIGRATE=False: test database setup should complete and allow tests to run with migrations skipped, without the reported missing-table serialization crash.

Update the supplied django/django repository to meet these requirements:
- Ensure test database setup completes with TEST.MIGRATE set to False, allowing tests to run with migrations skipped without the reported missing-table serialization crash.
Preserve unrelated existing behavior.

## django__django-13551.source.v1.840730ec69

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's PasswordResetTokenGenerator currently accepts an unused password reset link after the account's email address changes. I’m reviewing how outstanding reset links should behave during an email change, balancing continuity for users correcting their address against access through their former mailbox.
Preserve existing behavior outside the changes currently requested.

Please investigate how an email change affects outstanding password reset links. Should an unused link remain valid after the account's email address changes, or should that change invalidate it?

**U1**

Keep an unused password reset token valid when only the user's email address changes, so users correcting their address can still finish an already requested reset.

**U2**

Change the earlier policy of keeping those tokens valid: include the user's email address in PasswordResetTokenGenerator._make_hash_value() so previously issued, unused password reset tokens are rejected after the user's email changes.

Update the supplied django/django repository to meet these requirements:
- Include the user's email address in PasswordResetTokenGenerator._make_hash_value() so previously issued, unused password reset tokens are rejected after the user's email changes.
Preserve unrelated existing behavior.

## django__django-13590.source.v1.be09823f33

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In django/django, a project upgrading from Django 2.2 to 3.0 passes named two-tuples to QuerySet __range filters and encounters a TypeError about a missing constructor argument. Investigate how Query.resolve_lookup_value resolves the tuple elements and reconstructs the container, and establish an intentional handling policy for these inputs.
Preserve existing behavior outside the changes currently requested.

Please assess whether named two-tuples in __range lookups should be supported through reconstruction or explicitly rejected with a clear validation error requiring an ordinary two-tuple.

**U1**

Explicitly reject named two-tuples supplied to QuerySet __range lookups with a clear validation error directing callers to use an ordinary two-tuple.

**U2**

Replace the rejection policy with restored support for named two-tuples as QuerySet __range lookup arguments. When resolving lookup values and reconstructing a named tuple, expand the resolved elements into its constructor as positional arguments so reconstruction succeeds.

Update the supplied django/django repository to meet these requirements:
- Restore support for named two-tuples as QuerySet __range lookup arguments: when resolving lookup values and reconstructing a named tuple, expand the resolved elements into its constructor as positional arguments so reconstruction succeeds.
Preserve unrelated existing behavior.

## django__django-13658.source.v1.e27aa73dcd

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django's ManagementUtility, an embedded caller supplies an explicit argv while sys.argv[0] is None. The preliminary CommandParser used to parse --pythonpath and --settings currently derives its program name from sys.argv, causing this invocation to fail. Investigate the parser's program-label handling for this situation.
Preserve existing behavior outside the changes currently requested.

Please assess the preliminary parser's program label: should it use a fixed 'django-admin' label for consistent embedded diagnostics, or ManagementUtility's already-computed program name from the supplied argv?

**U1**

Give the preliminary CommandParser a fixed 'django-admin' program label, independent of the supplied argv and sys.argv, so embedded invocations have consistent diagnostic labels even when sys.argv[0] is None.

**U2**

Replace the fixed 'django-admin' label policy: have ManagementUtility pass its already-computed self.prog_name as the prog argument to the CommandParser used for --pythonpath and --settings. This parser should use the supplied argv's program name and work when sys.argv[0] is None.

Update the supplied django/django repository to meet these requirements:
- Make ManagementUtility pass its already-computed self.prog_name as the prog argument to the CommandParser used for --pythonpath and --settings, so that parser uses the supplied argv's program name and works when sys.argv[0] is None.
Preserve unrelated existing behavior.

## django__django-13710.source.v1.08b7d4e15e

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django admin Inline classes support verbose_name and verbose_name_plural. When an inline specifies only verbose_name, its plural currently comes from the model's naming metadata. I want to address how this configuration is handled.
Preserve existing behavior outside the changes currently requested.

Please investigate how to handle an admin Inline that sets verbose_name but omits verbose_name_plural. Should Django require an explicit plural or derive a default from the inline's verbose_name?

**U1**

Reject this configuration and require an explicit verbose_name_plural to avoid unintended pluralization.

**U2**

Replace the rejection policy with a derived default: when an admin Inline class specifies verbose_name but omits verbose_name_plural, base its default verbose_name_plural on that inline's verbose_name.

Update the supplied django/django repository to meet these requirements:
- When an admin Inline class specifies verbose_name but omits verbose_name_plural, base its default verbose_name_plural on that inline verbose_name.
Preserve unrelated existing behavior.

## django__django-13757.source.v1.371394161e

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied django/django repository. Django's JSONField KeyTransformIsNull lookup on SQLite currently conflates a missing key with a present key whose value is JSON null.
Preserve existing behavior outside the changes currently requested.

On SQLite, make KeyTransform queries using __isnull=True match only objects missing the queried key, excluding objects where the key exists with a JSON null value.

**U1**

Apply the same requirement on Oracle: KeyTransform queries using __isnull=True must match only objects missing the queried key, excluding objects where the key exists with a JSON null value.

Update the supplied django/django repository to meet these requirements:
- On SQLite, KeyTransform queries using __isnull=True must match only objects missing the queried key and exclude objects where that key exists with a JSON null value.
- On Oracle, KeyTransform queries using __isnull=True must match only objects missing the queried key and exclude objects where that key exists with a JSON null value.
Preserve unrelated existing behavior.

## django__django-13925.source.v1.aec603c953

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django 3.2 alpha, running makemigrations reports models.W042 for models whose primary key was manually declared on an ancestor. Investigate how the model check handles these inherited declarations.
Preserve existing behavior outside the changes currently requested.

Please investigate whether the model check should require a local primary-key declaration or honor a manually specified primary key inherited from an ancestor without emitting models.W042.

**U1**

Require a local primary-key declaration: reject models that inherit a manually specified primary key without declaring one locally, using a clear model validation error to enforce explicit key ownership.

**U2**

Replace the local-declaration requirement and its validation error with support for inherited declarations: do not emit models.W042 for models that inherit a manually specified primary key from an ancestor.

Update the supplied django/django repository to meet these requirements:
- Do not emit models.W042 for models that inherit a manually specified primary key from an ancestor.
Preserve unrelated existing behavior.

## django__django-13964.source.v1.ac98a73d63

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, assigning Product() to Order.product captures an empty foreign-key value when Product uses a non-auto CharField primary key. If the product then receives its SKU and is saved, saving the order still uses the captured empty value. I need the handling of this staged construction sequence addressed.
Preserve existing behavior outside the changes currently requested.

Please investigate how to handle the key change in this sequence. I'm unsure whether saving the order should reject the changed key or synchronize its foreign-key value with the product's current key.

**U1**

If the related object is assigned with an empty non-numeric primary key, then receives a key and is saved, saving the referencing object should raise an explicit validation error because its captured foreign-key value differs from the related object's current key.

**U2**

Change the validation-error policy to synchronization: when an unsaved related object with an initially empty non-numeric primary key is assigned to a foreign-key relation, then given a primary key and saved, saving the referencing object must persist the related object's current primary key rather than the stale empty value.

Update the supplied django/django repository to meet these requirements:
- When an unsaved related object with an initially empty non-numeric primary key is assigned to a foreign-key relation, then given a primary key and saved, saving the referencing object must persist the related object's current primary key instead of the stale empty value.
Preserve unrelated existing behavior.

## django__django-14016.source.v1.8904c4e45a

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's Q objects can hold query values such as dict_keys. Combining an empty Q object with Q(x__in={}.keys()) using | currently raises TypeError: cannot pickle 'dict_keys' object. Investigate how Q combination handles these values and establish the intended input policy.
Preserve existing behavior outside the changes currently requested.

Please check whether combining Q objects with | should require pickleable query values or support non-pickleable values such as dict_keys, including when either operand is an empty Q object.

**U1**

Require pickleable query values for Q combination with |. Explicitly reject operands containing non-pickleable values with a clear validation error, including when the other operand is an empty Q object.

**U2**

Replace the rejection policy with support for combining Q objects containing references to non-pickleable values, such as dict_keys, using | without a pickling TypeError, including when combined with an empty Q object.

Update the supplied django/django repository to meet these requirements:
- Allow Q objects containing references to non-pickleable values, such as dict_keys, to be combined with | without a pickling TypeError, including when combined with an empty Q object.
Preserve unrelated existing behavior.

## django__django-14017.source.v1.86f0f4d0d8

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied django/django repository. Django's ORM combines Q objects and Exists expressions into boolean query conditions. Combining these expression types currently behaves differently depending on operand order.
Preserve existing behavior outside the changes currently requested.

Allow Q and Exists expressions to be combined with & in either operand order without raising TypeError, with equivalent conjunction behavior.

**U1**

Also allow Q and Exists expressions to be combined with | in either operand order without raising TypeError, with equivalent disjunction behavior.

Update the supplied django/django repository to meet these requirements:
- Allow Q and Exists expressions to be combined with & in either operand order without TypeError, with equivalent conjunction behavior.
- Allow Q and Exists expressions to be combined with | in either operand order without TypeError, with equivalent disjunction behavior.
Preserve unrelated existing behavior.

## django__django-14155.source.v1.6d4060d0c3

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's ResolverMatch.__repr__() identifies a functools.partial view as functools.partial, making URL-resolution diagnostics difficult to interpret. The representation may appear in logs, so exposing arguments supplied to the partial involves a choice about diagnostic detail.
Preserve existing behavior outside the changes currently requested.

Please investigate the representation options. I'm unsure whether it should reveal both the underlying function and the partial's bound arguments, or show the function while keeping those arguments out of logs.

**U1**

For a functools.partial view, show the underlying function in ResolverMatch.__repr__(), but omit the arguments supplied in advance to keep their values out of diagnostic logs.

**U2**

Change the argument-visibility policy: when a functools.partial object is used as a view, ResolverMatch.__repr__() must reveal both its underlying function and the arguments supplied in advance.

Update the supplied django/django repository to meet these requirements:
- When a functools.partial object is used as a view, ResolverMatch.__repr__() must reveal its underlying function and the arguments supplied in advance.
Preserve unrelated existing behavior.

## django__django-14238.source.v1.ee73ff573d

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In django/django, DEFAULT_AUTO_FIELD validation runs when a model needs an implicit primary key. Configuring a custom BigAutoField subclass currently raises an AutoField subclass-validation error during model setup. Investigate this validation and the acceptance policy for custom subclasses in the BigAutoField and SmallAutoField families.
Preserve existing behavior outside the changes currently requested.

Please investigate whether DEFAULT_AUTO_FIELD should accept custom subclasses of BigAutoField and SmallAutoField or allow only the built-in classes within those two families. I'm unsure which policy is appropriate.

**U1**

For DEFAULT_AUTO_FIELD, deliberately reject custom subclasses of BigAutoField and SmallAutoField, allowing only the built-in classes within these two families.

**U2**

Replace the built-in-only policy with support for custom subclasses of both BigAutoField and SmallAutoField. Recognize these subclasses in AutoFieldMeta.__subclasscheck__ so that configuring them through DEFAULT_AUTO_FIELD allows implicit primary-key creation without the erroneous AutoField subclass-validation failure.

Update the supplied django/django repository to meet these requirements:
- Recognize subclasses of BigAutoField in AutoFieldMeta.__subclasscheck__ so that configuring one through DEFAULT_AUTO_FIELD allows implicit primary-key creation without the erroneous AutoField subclass-validation failure.
- Recognize subclasses of SmallAutoField in AutoFieldMeta.__subclasscheck__ so that configuring one through DEFAULT_AUTO_FIELD allows implicit primary-key creation without the erroneous AutoField subclass-validation failure.
Preserve unrelated existing behavior.

## django__django-14382.source.v1.c45c5329d9

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. django-admin startapp accepts a target directory argument. When that path ends in a slash, directory-name validation currently reports an empty name as invalid. Investigate how the command handles this input.
Preserve existing behavior outside the changes currently requested.

Please assess how trailing separators should be handled. I'm unsure whether otherwise valid target directory paths ending in slashes should be accepted or rejected with an explicit instruction to remove the trailing separators.

**U1**

Reject startapp target directory paths ending in a slash with an explicit error telling the caller to remove the trailing separators.

**U2**

Replace that rejection policy: make django-admin startapp accept otherwise valid target directory paths with trailing slashes by validating the directory name without those trailing separators.

Update the supplied django/django repository to meet these requirements:
- Make django-admin startapp accept otherwise valid target directory paths with trailing slashes by validating the directory name without those trailing separators.
Preserve unrelated existing behavior.

## django__django-14411.source.v1.0e84953f50

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django admin, ReadOnlyPasswordHashWidget renders a password hash summary as text. Its admin label currently has a 'for' attribute targeting a non-labelable element. The label presentation needs adjustment.
Preserve existing behavior outside the changes currently requested.

Please investigate the label handling. I'm unsure whether this text-only password summary should have its admin label suppressed entirely or retain a visible label without a 'for' attribute.

**U1**

Suppress the admin label entirely for ReadOnlyPasswordHashWidget to remove the invalid association from this text-only display.

**U2**

I'd like to revise the label-suppression requirement: retain the admin label for ReadOnlyPasswordHashWidget, but omit its 'for' attribute because the widget has no labelable element.

Update the supplied django/django repository to meet these requirements:
- Ensure the admin label for ReadOnlyPasswordHashWidget omits the 'for' attribute because the widget has no labelable element.
Preserve unrelated existing behavior.

## django__django-14752.source.v1.35936e473f

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied django/django repository. Django admin's AutocompleteJsonView.get() constructs autocomplete result dictionaries inline. Adding related-model attributes currently requires subclasses to copy the get() implementation, creating maintenance overhead as that method evolves.
Preserve existing behavior outside the changes currently requested.

Extract construction of the complete autocomplete results list into an overridable batch method so subclasses can add result fields without copying get(). Keep individual object conversion inside that batch method, without exposing a per-object serialization hook.

**U1**

Change the extension point from a batch method to an overridable serialize_result(self, obj, to_field_name) method, returning {'id': str(getattr(obj, to_field_name)), 'text': str(obj)} by default. Have get() call it for each result object so subclasses can add result fields without overriding get(), and preserve the existing pagination response.

Update the supplied django/django repository to meet these requirements:
- Refactor AutocompleteJsonView to expose serialize_result(self, obj, to_field_name), returning {'id': str(getattr(obj, to_field_name)), 'text': str(obj)} by default, and have get() use this overridable method for each result object. Subclasses must be able to add result fields through this method without overriding get(), while preserving the existing pagination response.
Preserve unrelated existing behavior.

## django__django-14787.source.v1.80c399ca30

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied django/django repository. Django's method_decorator() passes a callable to the supplied decorator. A logging decorator that accesses that callable's __name__ currently encounters an AttributeError because the callable is a functools.partial object without normal function metadata.
Preserve existing behavior outside the changes currently requested.

Give the callable passed by method_decorator() generic __name__ and __module__ metadata so logging decorators can access those attributes without exposing the original method's identity.

**U1**

Replace the generic-metadata policy with preserving wrapper-assigned function metadata, including __name__ and __module__, on the callable passed to the supplied decorator so decorators can access those attributes.

Update the supplied django/django repository to meet these requirements:
- Ensure method_decorator() preserves wrapper-assigned function metadata, including __name__ and __module__, on the callable passed to the supplied decorator so decorators can access those attributes.
Preserve unrelated existing behavior.

## django__django-14855.source.v1.0d04b4871b

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's admin get_admin_url generates links for readonly ForeignKey values. When viewing or editing a model in a custom Admin Site, these links currently point to /admin/... instead of the custom site's path. Investigate this behavior and the handling of these readonly related values.
Preserve existing behavior outside the changes currently requested.

Please check how these readonly values are handled. I'm unsure whether to remove their links and show plain text or preserve navigation by directing the links to the current Admin Site.

**U1**

When viewing or editing a model in a custom Admin Site, display ForeignKey fields listed in readonly_fields as plain text without links.

**U2**

Replace the plain-text requirement: when viewing or editing a model in a custom Admin Site, generate links for ForeignKey fields listed in readonly_fields using the current Admin Site's URL namespace.

Update the supplied django/django repository to meet these requirements:
- When viewing or editing a model in a custom Admin Site, generate links for ForeignKey fields listed in readonly_fields using the current Admin Site's URL namespace.
Preserve unrelated existing behavior.

## django__django-14997.source.v1.8c21c7f0c5

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django 4.0a1 on SQLite, a Tag model has an expression-based UniqueConstraint over name and value. Altering value's max_length triggers a table remake, and migration fails with OperationalError: the "." operator prohibited in index expressions. Investigate this migration failure and the handling of table remakes involving these constraints.
Preserve existing behavior outside the changes currently requested.

Please assess whether SQLite table remakes involving expression-based unique constraints should be rejected before rebuilding or supported by successfully recreating those constraints. I’m unsure which behavior is appropriate.

**U1**

Reject SQLite table-remaking operations involving expression-based unique constraints with a clear unsupported-operation error before rebuilding the table.

**U2**

Change the policy from rejecting these operations to supporting them. Ensure SQLite table remakes, including those triggered by field alterations, successfully recreate expression-based unique constraints without generating prohibited table-qualified references in index expressions.

Update the supplied django/django repository to meet these requirements:
- Ensure SQLite table-remaking operations, including those triggered by field alterations, successfully recreate expression-based unique constraints without generating prohibited table-qualified references in index expressions.
Preserve unrelated existing behavior.

## django__django-14999.source.v1.9f6ce79940

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's RenameModel currently performs database work even when the model has an explicit db_table: PostgreSQL foreign key constraints are dropped and recreated, and SQLite recreates the table. Investigate this case and establish how RenameModel should handle explicitly named tables.
Preserve existing behavior outside the changes currently requested.

Please investigate whether RenameModel should be rejected for a model with an explicit db_table or supported without changing the database. I'm unsure which behavior is appropriate.

**U1**

Reject RenameModel with a clear error when the model already has an explicit db_table.

**U2**

Change the policy from rejecting RenameModel to making it a database no-op when the model already has db_table explicitly defined, avoiding foreign key constraint recreation in PostgreSQL and table recreation in SQLite.

Update the supplied django/django repository to meet these requirements:
- Make RenameModel a database no-op when the model already has db_table explicitly defined, avoiding foreign key constraint recreation in PostgreSQL and table recreation in SQLite.
Preserve unrelated existing behavior.

## django__django-15061.source.v1.e61654d938

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's MultiWidget represents a single field using multiple subwidgets. Its id_for_label currently appends an index to the supplied ID, affecting which subwidget the outer field label targets. Review this label association.
Preserve existing behavior outside the changes currently requested.

Please investigate the outer label association. I'm unsure whether it should target the first subwidget for click-to-focus behavior or omit the for attribute because it describes the composite field.

**U1**

Keep MultiWidget's outer label associated with its first subwidget through the for attribute so clicking the label focuses that subwidget.

**U2**

Revise that decision: remove the for attribute from labels generated for MultiWidget, replacing the earlier requirement to associate the outer label with the first subwidget.

Update the supplied django/django repository to meet these requirements:
- Remove the for attribute from labels generated for MultiWidget.
Preserve unrelated existing behavior.

## django__django-15202.source.v1.88c0001903

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Investigate malformed URL handling in Django's forms.URLField.clean(). Calling forms.URLField().clean('////]@N.AN') reaches URL parsing and raises ValueError: Invalid IPv6 URL. The handling policy needs to account for a form that may preserve entered links for later correction.
Preserve existing behavior outside the changes currently requested.

Please assess how this parsing failure should be handled. Should clean() preserve the original input for later correction, or reject it with ValidationError?

**U1**

When malformed input triggers an invalid IPv6 URL parsing error during forms.URLField.clean(), return the original input unchanged so the form can preserve it for later correction.

**U2**

Revise that policy: when malformed URLs trigger an invalid IPv6 URL parsing error, forms.URLField.clean() should raise ValidationError rather than return the original input or leak ValueError.

Update the supplied django/django repository to meet these requirements:
- Ensure forms.URLField.clean() raises ValidationError rather than leaking ValueError when malformed URLs trigger an invalid IPv6 URL parsing error.
Preserve unrelated existing behavior.

## django__django-15213.source.v1.7d5e28f622

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django Boolean ExpressionWrapper annotations can receive Q expressions produced by reducing filters. Annotating with ExpressionWrapper(~Q(pk__in=[]), output_field=BooleanField()) currently produces an empty SQL expression before the annotation alias.
Preserve existing behavior outside the changes currently requested.

Please investigate how this annotation should be handled. I'm unsure whether Boolean ExpressionWrapper annotations containing negated empty-membership Q expressions should be explicitly rejected or supported using their Boolean value.

**U1**

Explicitly reject Boolean ExpressionWrapper annotations containing negated empty-membership Q expressions with a clear error.

**U2**

Replace that rejection policy with support: make Boolean ExpressionWrapper annotations containing negated empty-membership Q expressions generate valid SQL representing true, so the query succeeds.

Update the supplied django/django repository to meet these requirements:
- Make Boolean ExpressionWrapper annotations containing negated empty-membership Q expressions generate valid SQL representing true, so the query succeeds.
Preserve unrelated existing behavior.

## django__django-15347.source.v1.b2dfd2900e

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's messages framework changes extra_tags from an empty string to None when a message passes through serialization and deserialization in built-in storage. This can break template expressions that check membership in message.extra_tags after a redirect.
Preserve existing behavior outside the changes currently requested.

Please investigate how built-in message storage handles empty-string extra_tags. Should it reject that value as invalid input, or preserve it through serialization and deserialization?

**U1**

Reject messages whose extra_tags is an empty string with a clear validation error when serializing them through built-in storage backends.

**U2**

Replace the rejection policy with preserving extra_tags as an empty string through serialization and deserialization in every built-in storage backend, including for messages created through standard message APIs with the default extra_tags value.

Update the supplied django/django repository to meet these requirements:
- Preserve extra_tags as an empty string when messages are serialized and deserialized through any built-in storage backend, including messages created using standard message APIs with the default extra_tags value.
Preserve unrelated existing behavior.

## django__django-15388.source.v1.fa5926aaa8

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's development server stops reacting to file saves when BASE_DIR is placed in TEMPLATES[0]['DIRS']. Investigate how using the project directory as a template directory interacts with development-server autoreloading.
Preserve existing behavior outside the changes currently requested.

Please investigate whether the development server should reject this configuration with a clear error or support it while detecting file changes and restarting automatically. I'm unsure which behavior is appropriate.

**U1**

When BASE_DIR is included in TEMPLATES[0]['DIRS'], reject the configuration with a clear error when starting the development server.

**U2**

Replace the startup-error requirement with support for this configuration: the development server should detect file changes and automatically restart when BASE_DIR is included in TEMPLATES[0]['DIRS'], including changes outside settings.py.

Update the supplied django/django repository to meet these requirements:
- Ensure Django's development server detects file changes and automatically restarts when BASE_DIR is included in TEMPLATES[0]['DIRS'], including changes outside settings.py.
Preserve unrelated existing behavior.

## django__django-15498.source.v1.2f171b41d0

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django now raises an exception when a request contains an empty If-Modified-Since header, following d6aff369ad3. Investigate this case while I review the appropriate validation policy.
Preserve existing behavior outside the changes currently requested.

Check how the empty header triggers the exception. I’m undecided whether an empty If-Modified-Since header should cause controlled request rejection or be ignored.

**U1**

Reject requests containing an empty If-Modified-Since header with a controlled HTTP 400 response so malformed client requests are visible.

**U2**

Replace the HTTP 400 policy with ignoring an empty string value for the If-Modified-Since header without raising an exception.

Update the supplied django/django repository to meet these requirements:
- Ignore an empty string value for the If-Modified-Since header without raising an exception.
Preserve unrelated existing behavior.

## django__django-15738.source.v1.70521a1820

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django migrations fail when Authors.project_data_set changes from ForeignKey to ManyToManyField while the unique_together containing project_data_set, state, and start_date is removed. Applying the generated migration raises ValueError about finding zero constraints. This affects a production database with existing migration history, and the handling of these simultaneous model changes needs investigation.
Preserve existing behavior outside the changes currently requested.

Please assess whether these simultaneous changes should be explicitly rejected with a requirement to use separate migrations, or supported in one generated migration while preserving existing migration history. I'm unsure which approach Django should take.

**U1**

When unique_together is removed while an included ForeignKey is converted to ManyToManyField, reject the combined change during makemigrations with a clear explanation requiring separate migrations.

**U2**

Replace the requirement to reject the combined change and require separate migrations: allow removing unique_together and converting an included ForeignKey to ManyToManyField in a single generated migration that applies successfully without deleting existing migration history.

Update the supplied django/django repository to meet these requirements:
- Allow removing unique_together and converting an included ForeignKey to a ManyToManyField in a single generated migration that applies successfully without deleting existing migration history.
Preserve unrelated existing behavior.

## django__django-15781.source.v1.76d3c32596

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django management command help collapses explicit line breaks and indentation in multiline help strings, including indented usage examples. I’m reviewing formatter selection for commands whose help contains different mixtures of prose and examples.
Preserve existing behavior outside the changes currently requested.

Please review the formatter-selection options. Should all management commands share one fixed formatter that preserves whitespace, or should individual commands be able to customize their help formatter?

**U1**

Use one fixed formatter for all management commands that preserves explicit line breaks and indentation, without allowing commands to select their own formatter.

**U2**

Replace the fixed-formatter policy with support for management commands to customize their help formatter so multiline command help can preserve explicit line breaks and indentation.

Update the supplied django/django repository to meet these requirements:
- Allow management commands to customize their help formatter so multiline command help can preserve explicit line breaks and indentation.
Preserve unrelated existing behavior.

## django__django-15789.source.v1.a99d97a5ed

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. django.utils.html.json_script() currently hardcodes DjangoJSONEncoder when serializing values for templates. I need to customize how some values are encoded.
Preserve existing behavior outside the changes currently requested.

Please investigate support for custom encoder classes. I'm unsure whether they should be required to subclass DjangoJSONEncoder or whether any JSON encoder class should be accepted.

**U1**

Add an optional encoder parameter to json_script(), keeping DjangoJSONEncoder as the default. Require custom encoder classes to subclass DjangoJSONEncoder and reject those that don't.

**U2**

Remove the subclass restriction: the optional encoder parameter should accept any JSON encoder class. Keep DjangoJSONEncoder as the default.

Update the supplied django/django repository to meet these requirements:
- Add an optional encoder parameter to django.utils.html.json_script() that accepts a custom JSON encoder class, retaining DjangoJSONEncoder as the default.
Preserve unrelated existing behavior.

## django__django-15790.source.v1.e0b592e240

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, check_for_template_tags_with_the_same_name reports templates.E003 for a template tag library configured through TEMPLATES['OPTIONS']['libraries'], listing the same module path twice under the same name. Investigate how configured libraries enter this check and establish how repeated registrations should be handled.
Preserve existing behavior outside the changes currently requested.

Please look into whether repeated registrations under the same library name pointing to the identical module should be rejected as redundant or accepted as references to one library.

**U1**

Treat repeated registrations under the same template tag library name as a configuration error. Report templates.E003 even when the module paths are identical, explicitly rejecting redundant registration.

**U2**

Replace the rejection policy: check_for_template_tags_with_the_same_name should not report templates.E003 when a library configured through TEMPLATES['OPTIONS']['libraries'] has repeated references to the identical module under the same name.

Update the supplied django/django repository to meet these requirements:
- Prevent check_for_template_tags_with_the_same_name from reporting templates.E003 when a template tag library configured through TEMPLATES['OPTIONS']['libraries'] has repeated references to the identical module under the same name.
Preserve unrelated existing behavior.

## django__django-15814.source.v1.0039847ca0

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, AnotherModel.custom is a nullable ForeignKey to ProxyCustomModel, a proxy of CustomModel with a name field. Evaluating AnotherModel.objects.select_related("custom").only("custom__name") raises ValueError: 'id' is not in list during related-object population. Investigate how this combination should be handled.
Preserve existing behavior outside the changes currently requested.

Please investigate whether this combination should be explicitly rejected as unsupported or supported so the queryset evaluates with the requested field selection.

**U1**

Explicitly reject querysets combining select_related() with only() for fields on a related proxy model. Raise a clear validation error explaining that this combination is unsupported.

**U2**

Change the policy from rejecting this combination to supporting it. Ensure these querysets evaluate successfully, preserving the requested field selection without the missing-primary-key crash.

Update the supplied django/django repository to meet these requirements:
- Ensure querysets combining select_related() with only() for fields on a related proxy model evaluate successfully, preserving the requested field selection without the missing-primary-key crash.
Preserve unrelated existing behavior.

## django__django-15819.source.v1.4cb443ccab

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's inspectdb generates model fields from database relations. When a table has multiple relations to the same model, the generated reverse accessors can clash and produce fields.E304 errors.
Preserve existing behavior outside the changes currently requested.

Please investigate how to handle these clashes. Should inspectdb reject generation and require explicit relation naming, or generate related_name arguments that prevent reverse-accessor clashes?

**U1**

When a table has multiple relations to the same model, reject model generation with a clear error explaining that explicit relation naming is required.

**U2**

Replace the rejection policy: have inspectdb generate appropriate related_name arguments for multiple relations from a table to the same model so their reverse accessors do not clash.

Update the supplied django/django repository to meet these requirements:
- Make inspectdb generate appropriate related_name arguments for multiple relations to the same model so their reverse accessors do not clash.
Preserve unrelated existing behavior.

## django__django-15851.source.v1.4089947435

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's PostgreSQL dbshell can ignore additional parameters when a database name is supplied. For example, passing `-c "select * from some_table;"` produces psql warnings that the arguments were ignored and opens an interactive prompt. This makes the invocation unreliable for automation, and I need to establish how dbshell should handle this combination.
Preserve existing behavior outside the changes currently requested.

Please investigate how to handle this combination. I'm unsure whether to reject the invocation explicitly or support passing the additional parameters so psql honors them.

**U1**

When PostgreSQL dbshell receives both a database name and additional parameters, reject the invocation with an explicit error before launching psql.

**U2**

Replace the earlier rejection policy with support for this combination: construct PostgreSQL dbshell arguments with additional parameters before the database name, keeping the database name last when supplied, so psql honors the additional parameters.

Update the supplied django/django repository to meet these requirements:
- Construct PostgreSQL dbshell arguments with additional parameters before the database name, leaving the database name last when supplied, so psql honors the additional parameters.
Preserve unrelated existing behavior.

## django__django-15996.source.v1.8b5f6a9bb9

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's migration EnumSerializer uses an enum value's .name. A field default such as models.IntegerField(default=re.UNICODE | re.IGNORECASE) can consequently serialize as default=re.RegexFlag[None] when the combination lacks a single member name.
Preserve existing behavior outside the changes currently requested.

Please investigate handling combined Enum flag defaults that lack a single member name. Should migration serialization explicitly reject these values or support reconstructing the combination?

**U1**

When a combined Enum flag default lacks a single member name, reject migration serialization with a clear error.

**U2**

Replace the rejection policy with support for these combined Enum flag values: emit an expression that reconstructs the value by bitwise ORing named members.

Update the supplied django/django repository to meet these requirements:
- Django migration serialization must support combined Enum flag values lacking a single member name by emitting an expression that reconstructs the value by bitwise ORing named members.
Preserve unrelated existing behavior.

## django__django-16041.source.v1.13e506f987

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Rendering a Django formset's empty_form raises a KeyError when form_kwargs explicitly includes empty_permitted, whether True or False. Investigate how empty_form handles this supplied option and establish an intentional handling policy.
Preserve existing behavior outside the changes currently requested.

Please assess whether explicitly supplying empty_permitted through form_kwargs should cause empty_form to reject the configuration with a clear error or ignore the option. I'm unsure which policy is appropriate.

**U1**

When form_kwargs explicitly supplies empty_permitted as either True or False, deliberately reject access to formset.empty_form with a clear configuration error.

**U2**

Change the policy from rejecting the configuration to ignoring empty_permitted supplied through form_kwargs for formset.empty_form, whether True or False, so empty_form renders without the reported KeyError.

Update the supplied django/django repository to meet these requirements:
- Ignore empty_permitted supplied through form_kwargs for formset.empty_form, whether True or False, so empty_form renders without the reported KeyError.
Preserve unrelated existing behavior.

## django__django-16046.source.v1.5a9d39d225

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's admin list_display crashes when formatting a null numeric field. In numberformat.py, the check `if str_number[0] == "-"` raises `IndexError: string index out of range`.
Preserve existing behavior outside the changes currently requested.

Please investigate the crash. I'm unsure whether we should remove nullable numeric columns from the admin list_display or fix numberformat.py so those fields can be formatted without this IndexError.

**U1**

Remove nullable numeric columns from the admin list_display so their values don't reach the failing formatter.

**U2**

Replace the column-removal approach with a fix in numberformat.py so formatting null numeric fields for the admin list_display does not raise IndexError: string index out of range.

Update the supplied django/django repository to meet these requirements:
- Fix numberformat.py so formatting null numeric fields for the admin list_display does not raise IndexError: string index out of range.
Preserve unrelated existing behavior.

## django__django-16139.source.v1.aa6ccb47f6

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's UserAdmin can be opened from a related model through a non-primary-key to_field, producing a URL such as /user/22222222-3333-4444-5555-666677778888/change/?_to_field=uuid. UserChangeForm's password help text links to ../password/, which leads to a 404 from this entry point. Review how password-change access should behave in this situation.
Preserve existing behavior outside the changes currently requested.

Please investigate this entry path. I'm unsure whether the password-change help link should be omitted or remain available and lead to the correct user's password-change page.

**U1**

When UserAdmin is accessed through a related model using a non-primary-key to_field value, omit the password-change help link.

**U2**

Replace my earlier instruction to omit the link: keep UserChangeForm's password-change help link available and make it resolve to the correct user's password-change page when UserAdmin is accessed through a related model using a non-primary-key to_field value.

Update the supplied django/django repository to meet these requirements:
- Make UserChangeForm's password-change help link resolve to the correct user's password-change page when UserAdmin is accessed through a related model using a non-primary-key to_field value.
Preserve unrelated existing behavior.

## django__django-16229.source.v1.67caf67a43

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django admin object creation, an inline containing an ArrayField with default=list reports a validation error on the first submission, but submitting again without changes dismisses the inline and loses its entered value. The field's hidden initial input appears related. Investigate callable-default handling in these inline ModelForms and establish how such fields should be handled.
Preserve existing behavior outside the changes currently requested.

Please assess whether admin inlines with callable-default fields should be rejected with an explicit error as a safeguard or remain supported through repeated validation. I’m unsure which approach is appropriate.

**U1**

Reject admin object creation when an inline ModelForm contains a field with a callable default. Report an explicit unsupported-configuration error to prevent silent loss of inline data.

**U2**

Replace the rejection policy with a correction to default-value propagation for ModelForm fields with callable defaults. An invalid admin inline, including one containing an ArrayField with a callable default, must retain its entered values and continue reporting validation errors when resubmitted without modification, rather than being dismissed.

Update the supplied django/django repository to meet these requirements:
- Correct default-value propagation for ModelForm fields with callable defaults so that an invalid admin inline, including one containing an ArrayField with a callable default, retains its entered values and continues to report validation errors when resubmitted without modification instead of being dismissed.
Preserve unrelated existing behavior.

## django__django-16255.source.v1.bda8db1ce8

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django's sitemap index, Sitemap.get_latest_lastmod() evaluates callable lastmod over the sitemap's items. When there are no items, its max() call raises an empty-sequence ValueError.
Preserve existing behavior outside the changes currently requested.

Please investigate the empty-sitemap failure in get_latest_lastmod(). I’m unsure whether an empty sitemap with callable lastmod should be rejected as a configuration error or accepted as having no latest modification date.

**U1**

When a sitemap has no items and lastmod is callable, deliberately reject it with a clear validation error identifying the empty sitemap, so configuration mistakes are visible.

**U2**

Replace the validation-error requirement: make Sitemap.get_latest_lastmod() return None when the sitemap has no items and lastmod is callable, so the sitemap index does not fail with an empty-sequence ValueError.

Update the supplied django/django repository to meet these requirements:
- Make Sitemap.get_latest_lastmod() return None when the sitemap has no items and lastmod is callable, so the sitemap index does not fail with an empty-sequence ValueError.
Preserve unrelated existing behavior.

## django__django-16379.source.v1.83177dc86b

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's FileBasedCache.has_key() checks whether a cache file exists before opening it. With concurrent cache access, the file can disappear between those operations and cause FileNotFoundError. Investigate this race and establish how a disappearing file should affect the cache lookup.
Preserve existing behavior outside the changes currently requested.

Please investigate the disappearing-file case. I'm unsure whether has_key() should treat it as a cache miss or surface an explicit cache consistency error.

**U1**

If the cache file disappears between the existence check and opening it, fail the lookup with a descriptive RuntimeError identifying the cache key, so unexpected deletion is visible.

**U2**

Replace the RuntimeError policy: FileBasedCache.has_key() should return False without raising FileNotFoundError when the cache file disappears between the existence check and opening it, including during concurrent expiration checks.

Update the supplied django/django repository to meet these requirements:
- Make FileBasedCache.has_key() return False without raising FileNotFoundError when a cache file disappears between the existence check and opening it, including during concurrent expiration checks.
Preserve unrelated existing behavior.

## django__django-16400.source.v1.af8400099e

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django's migrate command is being used with an explicit database alias in a multi-tenant service. Its custom database router relies on request-local tenant state, which is unavailable during management commands. Schema migration succeeds, but subsequent database access while adding permissions invokes the router and raises an exception. The command needs a deliberate policy for this situation.
Preserve existing behavior outside the changes currently requested.

Please investigate this migrate failure. When an explicit database alias is supplied but tenant routing lacks request-local context, should the command reject the operation before applying migrations or use the supplied alias for every database operation?

**U1**

When migrate receives an explicit database alias but the tenant router cannot select a database without request-local context, reject the command before applying migrations.

**U2**

Change the policy from rejecting the command to honoring the explicitly supplied database for all database operations within migrate, including reads performed when adding permissions, without falling back to router-based database selection.

Update the supplied django/django repository to meet these requirements:
- Ensure all database operations within migrate honor the explicitly supplied database, including reads performed when adding permissions, without falling back to router-based database selection.
Preserve unrelated existing behavior.

## django__django-16408.source.v1.ace8c7f25c

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django's ORM, a PoolStyle query annotates tournament_pool with FilteredRelation('pool__tournament__pool') and calls select_related('tournament_pool'). Accessing the resulting tournament relationships can yield a PoolStyle instance where a Tournament instance belongs. Investigate how this combination handles related-object assignment.
Preserve existing behavior outside the changes currently requested.

Investigate whether select_related() should explicitly reject multi-level FilteredRelation annotations or support them with correct related-object assignment. I'm unsure which approach is appropriate.

**U1**

Reject select_related() traversals through multi-level FilteredRelation annotations with an explicit error to prevent returning incorrectly assigned related objects.

**U2**

Replace the earlier rejection policy with support for these traversals: correct related-object assignment when select_related() follows multi-level FilteredRelation annotations so related attributes contain the correct model instances.

Update the supplied django/django repository to meet these requirements:
- Correct related-object assignment when select_related() follows multi-level FilteredRelation annotations, ensuring related attributes contain the correct model instances.
Preserve unrelated existing behavior.

## django__django-16595.source.v1.dee8a484a7

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django's migration optimizer, successive AlterField operations can remain unreduced when there is no AddField available to absorb them. The operations may change both database field properties, such as max_length, and descriptive properties, such as help_text. Investigate optimization of these standalone chains.
Preserve existing behavior outside the changes currently requested.

Please assess whether reduction of these standalone chains should be limited to metadata-only changes or should also collapse changes to the database field definition.

**U1**

For successive AlterField operations on the same model field without an absorbing AddField, collapse only metadata-only changes. Preserve intermediate operations that change the database field definition.

**U2**

Replace the metadata-only restriction with reduction to the final AlterField operation for successive changes to the same model field, including changes to the database field definition and chains without an absorbing AddField.

Update the supplied django/django repository to meet these requirements:
- Reduce successive AlterField operations on the same model field to the final AlterField operation, including when no AddField operation is available to absorb them.
Preserve unrelated existing behavior.

## django__django-16820.source.v1.f55205c361

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, I’m working on squashing migration histories that transition from Meta.index_together to Meta.indexes. Deprecated options in historical migrations complicate this cleanup, and I need to establish how squashing should handle these histories.
Preserve existing behavior outside the changes currently requested.

Please investigate how squashing handles these histories. Should it reject histories containing the deprecated Meta.index_together transition, or support squashing them and eliminate the associated warnings?

**U1**

Reject squashing histories that transition from Meta.index_together to Meta.indexes, and explain that the deprecated option must first be removed from the migration history.

**U2**

Replace the rejection policy: squashing migrations that transition from Meta.index_together to Meta.indexes must remove the associated index_together deprecation warnings.

Update the supplied django/django repository to meet these requirements:
- Squashing migrations that transition from Meta.index_together to Meta.indexes must remove the associated index_together deprecation warnings.
Preserve unrelated existing behavior.

## django__django-16873.source.v1.4c1f5b6065

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. Django’s template join filter escapes a variable joining string inside an autoescape-off block even though it leaves the list items unescaped. For example, a separator containing <br/> appears as escaped text. Investigate this handling and the policy for HTML-sensitive separators under autoescape off.
Preserve existing behavior outside the changes currently requested.

Please determine whether HTML-sensitive joining strings should be rejected when autoescape is off or inserted without escaping.

**U1**

When autoescape is off, reject join operations whose joining string contains HTML-sensitive characters.

**U2**

Replace the rejection policy with this behavior: when autoescape is off, leave the joining string unescaped and join the list items with it, without escaping either the items or the joining string.

Update the supplied django/django repository to meet these requirements:
- When autoescape is off, the template join filter must leave the joining string unescaped, producing the list items joined by that string without escaping either.
Preserve unrelated existing behavior.

## django__django-16910.source.v1.ba47cd5d2c

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In django/django, combining QuerySet.only() with select_related() through a reverse OneToOneField relation fetches unrequested related-model columns on Django 4.2. The affected operation needs investigation so that callers requesting a limited set of related fields receive deliberate handling.
Preserve existing behavior outside the changes currently requested.

Please investigate this interaction. I'm unsure whether requesting a subset of related fields with only() should be explicitly rejected or supported when select_related() traverses a reverse OneToOneField relation.

**U1**

Explicitly reject queries that combine select_related() across a reverse OneToOneField relation with only() requesting a subset of the related model's fields.

**U2**

Change the rejection policy to support the requested field selection: make QuerySet.only() honor it when select_related() traverses reverse OneToOneField relations, excluding unrequested related-model fields from the generated SQL while retaining required identifying keys.

Update the supplied django/django repository to meet these requirements:
- Make QuerySet.only() honor the requested field selection when used with select_related() across reverse OneToOneField relations, excluding unrequested related-model fields from the generated SQL while retaining required identifying keys.
Preserve unrelated existing behavior.

## django__django-17087.source.v1.aa8416118b

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied django/django repository. In Django, using a nested class's class method as Field.default can generate an invalid callable reference in a migration. For example, Profile.Capability.default is serialized as appname.models.Capability.default, and applying the migration fails. Investigate how migration serialization handles this situation.
Preserve existing behavior outside the changes currently requested.

Please assess whether migration serialization should explicitly reject nested class-method defaults or support them by generating a reference to the correct callable. I'm unsure which behavior is appropriate.

**U1**

Reject a nested class's class method used as Field.default with an explicit migration serialization error.

**U2**

Replace the rejection behavior with support: when a nested class's class method is used as Field.default, serialize its complete enclosing-class path in generated migrations so the default references the correct callable.

Update the supplied django/django repository to meet these requirements:
- When a class method of a nested class is used as Field.default, serialize its complete enclosing-class path in generated migrations so the default references the correct callable.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-22835.source.v1.c7e663e1d8

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib scalar mappables format cursor data for image values. A normalization may not support inversion; determine the desired cursor behavior in that case.

Please preserve existing behavior outside the requested change. I’m not sure what cursor formatting should display or do when it encounters a norm that cannot be inverted.

**U1**

Please preserve existing behavior outside this change. For a scalar mappable using BoundaryNorm, avoid the non-invertible norm error when formatting cursor data so cursor interaction continues.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- When formatting cursor data for a scalar mappable whose norm is BoundaryNorm, avoid the non-invertible norm error so that cursor interaction continues.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-23299.source.v1.26864d0fd1

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib's get_backend() interacts with pyplot's managed-figure registry after a figure is created in an rc_context().

Please preserve existing behavior outside the requested change. I’m not sure what should happen to a figure created inside `rc_context()` when `get_backend()` is called—should it remain in `Gcf.figs`?

**U1**

Please keep a figure created inside `rc_context()` in `Gcf.figs` when it is the first figure there and `get_backend()` is called, so pyplot operations such as `plt.close(fig)` can still find it. Preserve existing behavior outside this change.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- When the first figure in Gcf.figs was created inside rc_context(), calling get_backend() must preserve that figure in Gcf.figs so pyplot operations such as plt.close(fig) can find it.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-23314.source.v1.c80a11b642

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib's 3D subplot visibility behavior when calling `set_visible()` is at issue.

Please preserve existing behavior outside the requested changes. I’m not sure what should happen to a 3D subplot’s visibility when `set_visible(False)` is called.

**U1**

For a subplot created with `projection="3d"`, calling `set_visible(False)` should make it not visible. Please continue preserving unrelated existing behavior.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- For a subplot created with `projection="3d"`, calling `set_visible(False)` makes the subplot not visible.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-23476.source.v1.8b17ced85f

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib figure serialization and restoration can affect a figure's DPI. What DPI behavior should users expect after unpickling?
Preserve existing behavior outside the changes currently requested.

What should happen to a figure’s DPI when it’s unpickled on an M1 Mac using the MacOSX backend?

**U1**

On M1 Macs using the MacOSX backend, a figure’s DPI should remain unchanged across repeated pickle round trips.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- On M1 Macs using the MacOSX backend, unpickling a figure preserves its DPI across repeated pickle round trips.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-25311.source.v1.9b398fb6f8

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib figures can be serialized with Python pickle, and artists such as legends and annotations can be made draggable. The report describes a pickling error when using draggable interactions.
Preserve existing behavior outside the changes currently requested.

Please make a figure with a draggable legend pickle successfully.

**U1**

Also make a figure with draggable annotations pickle successfully.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- Allow a figure with a draggable legend to be pickled successfully.
- Allow a figure with draggable annotations to be pickled successfully.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-25433.source.v1.744ef969e0

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied matplotlib/matplotlib repository. In Matplotlib, a RangeSlider on_changed callback calls pyplot.clf(), recreates the slider and button, and calls pyplot.draw(). Afterwards, the widgets stop receiving mouse input. The same sequence inside a Button on_clicked callback works. Investigate how figure rebuilding during an active slider callback should be handled.
Preserve existing behavior outside the changes currently requested.

I'm unsure whether clearing, rebuilding, and redrawing the figure inside a RangeSlider on_changed callback should support continued mouse interaction or be explicitly rejected so rebuilding must use the button workflow.

**U1**

Explicitly reject attempts to clear and rebuild the figure inside a RangeSlider on_changed callback with a clear error. Use the Button on_clicked workflow for rebuilding.

**U2**

Replace that rejection policy: after a RangeSlider on_changed callback clears and rebuilds the figure and redraws it, widgets in the figure must continue receiving mouse input, as they do when the same work happens in a Button on_clicked callback.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- After a RangeSlider on_changed callback clears and rebuilds the figure and redraws it, widgets in the figure must continue to receive mouse input, as they do when the same work is done in a Button on_clicked callback.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-25498.source.v1.b70b4706f6

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied matplotlib/matplotlib repository. Matplotlib colorbars are associated with a mappable, whose normalization controls the mapping from data values to colors. When an application replaces that mappable's norm instance, the colorbar may need to refresh its displayed mapping.
Preserve existing behavior outside the changes currently requested.

If an application replaces a mappable's norm instance, should updating its colorbar refresh the displayed mapping from the new norm?

**U1**

Please ensure a colorbar can be updated after its mappable's norm instance changes, without the update having no effect or raising the reported ZeroDivisionError.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- Ensure a colorbar can be updated after the norm instance of its mappable is changed, without the update having no effect or raising the reported ZeroDivisionError.
Preserve unrelated existing behavior.

## matplotlib__matplotlib-26020.source.v1.304c8017fb

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied matplotlib/matplotlib repository. In `mpl_toolkits.axes_grid1.axes_grid.AxesGrid`, the `axis_class` argument controls which axes are created, and construction configures their ticks through `_tick_only`.
Preserve existing behavior outside the changes currently requested.

In `AxesGrid`, reject a supplied axes class with a callable `axis` attribute clearly, before attempting tick setup.

**U1**

Change that requirement: `AxesGrid` should support supplied axes classes with a callable `axis` attribute, allowing grid construction and tick setup to complete without the reported `TypeError`.

Update the supplied matplotlib/matplotlib repository to meet these requirements:
- AxesGrid must support supplied axes classes whose axis attribute is callable, allowing grid construction and tick setup to complete without the reported TypeError.
Preserve unrelated existing behavior.

## mwaskom__seaborn-2848.source.v1.4a1cc4b3cb

Class: `clarification`; updates: `clarification -> clarification`.

**U0**

Work in the supplied mwaskom/seaborn repository. In seaborn 0.11.1, calling pairplot with a hue_order that omits a species from the hue column raises a TypeError. How should pairplot behave when hue_order lists only some of the hue values?
Preserve existing behavior outside the changes currently requested.

In seaborn 0.11.1, `pairplot` raises a `TypeError` when `hue_order` omits a species from the hue column. How should `pairplot` handle hue values that are missing from `hue_order`?

**U1**

Please allow `pairplot` to accept a `hue_order` list that includes only some of the values in the hue column.

**U2**

For omitted hue values, plot only observations whose hue values appear in `hue_order`; skip the other observations and do not raise an error.

Update the supplied mwaskom/seaborn repository to meet these requirements:
- When pairplot receives a hue_order list that omits values present in the hue column, plot only observations whose hue values are in hue_order; do not plot observations with other hue values, and do not raise an error.
Preserve unrelated existing behavior.

## mwaskom__seaborn-3190.source.v1.a600873668

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied mwaskom/seaborn repository. Seaborn's objects Plot maps a color variable through scale setup. What behavior should it provide when that variable contains boolean values?
Preserve existing behavior outside the changes currently requested.

What should happen when an objects Plot maps a color variable containing boolean values?

**U1**

Please make color mapping work in an objects Plot when the color data contains boolean values, including with `so.Plot(["a", "b"], [1, 2], color=[True, False]).add(so.Bar())`.

Update the supplied mwaskom/seaborn repository to meet these requirements:
- Color mapping in an objects Plot must work when the color data contains boolean values, including the shown `so.Plot(["a", "b"], [1, 2], color=[True, False]).add(so.Bar())` example.
Preserve unrelated existing behavior.

## mwaskom__seaborn-3407.source.v1.26a831be39

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied mwaskom/seaborn repository. Seaborn's pairplot accepts a DataFrame and builds a grid of plots from its columns. A DataFrame with MultiIndex columns currently fails during plotting; what column handling should pairplot provide for this input?

I’ll preserve existing behavior outside the requested change. Should pairplot support DataFrames with MultiIndex columns directly, without requiring callers to flatten them?

**U1**

Please make pairplot successfully plot DataFrames with MultiIndex columns without requiring callers to flatten them first. Preserve existing behavior outside this change.

Update the supplied mwaskom/seaborn repository to meet these requirements:
- pairplot must successfully plot a DataFrame with MultiIndex columns without requiring the caller to flatten those columns first.
Preserve unrelated existing behavior.

## pydata__xarray-5131.source.v1.97ee7917e7

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pydata/xarray repository. In xarray, displaying a DatasetGroupBy produces a textual representation. The issue asks whether its current formatting should change.
Preserve existing behavior outside the changes currently requested.

Should the first line of a DatasetGroupBy text representation have its trailing space removed?

**U1**

Yes: remove trailing whitespace from the first line while preserving the rest of the representation, including its newline and following group summary.

Update the supplied pydata/xarray repository to meet these requirements:
- The first line of a DatasetGroupBy text representation must not have trailing whitespace; preserve the rest of the representation, including its newline and following group summary.
Preserve unrelated existing behavior.

## pylint-dev__pylint-5859.source.v1.85e93ff5c4

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pylint-dev/pylint repository. Pylint’s `--notes` option configures which comment tags trigger fixme warnings (W0511).

I’ll look into preserving existing behavior while updating how `--notes` handles punctuation-only tags. Should tags made entirely of punctuation in comments trigger W0511 fixme warnings?

**U1**

Yes—tags specified with `--notes` that consist entirely of punctuation should trigger a W0511 fixme warning when they appear in comments. Preserve unrelated existing behavior.

Update the supplied pylint-dev/pylint repository to meet these requirements:
- For note tags specified with `--notes` that consist entirely of punctuation, report a W0511 fixme warning for comments containing those tags.
Preserve unrelated existing behavior.

## pylint-dev__pylint-7080.source.v1.ac70b4a37a

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pylint-dev/pylint repository. Pylint recursively discovers Python files under a source directory and applies configured path exclusions.

Please preserve existing behavior outside the changes requested. For recursive runs, should files matching the configured ignore-paths pattern be skipped?

**U1**

Please also skip files matching the configured ignore-paths pattern during recursive runs; with the reported configuration, files under src/gen/ should be skipped.

Update the supplied pylint-dev/pylint repository to meet these requirements:
- When running recursively, do not check files matching the configured ignore-paths pattern; in the reported configuration, files under src/gen/ must be skipped.
Preserve unrelated existing behavior.

## pylint-dev__pylint-7993.source.v1.5f0b4076d1

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pylint-dev/pylint repository. Pylint's text reporter formats messages using the --msg-template option. The issue reports a regression when that template contains braces around a literal dictionary-like string and a category field.
Preserve existing behavior outside the changes currently requested.

The text reporter’s `--msg-template` option has a regression when a template combines literal dictionary braces with a category field. What should happen to the braces and the `{category}` field?

**U1**

For `--msg-template='{{ "Category": "{category}" }}'`, print the dictionary with `"Category"` as the key and the interpolated category value.

Update the supplied pylint-dev/pylint repository to meet these requirements:
- For `--msg-template='{{ "Category": "{category}" }}'`, print the dictionary with `"Category"` as the key and the interpolated category value.
Preserve unrelated existing behavior.

## pytest-dev__pytest-11143.source.v1.e150b2671e

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pytest-dev/pytest repository. pytest assertion rewriting processes test modules during collection and checks module docstrings for a rewrite-disable marker.

I’m not sure how assertion rewriting should handle a module whose first expression is numeric and is treated as its docstring during collection. Please preserve existing behavior outside the requested changes.

**U1**

When checking a module docstring for the rewrite-disable marker, handle a numeric first expression without raising a TypeError during test collection.

Update the supplied pytest-dev/pytest repository to meet these requirements:
- When assertion rewriting checks whether to disable rewriting based on a module docstring, handle a numeric first expression without raising TypeError during test collection.
Preserve unrelated existing behavior.

## pytest-dev__pytest-5692.source.v1.cc38bae5fb

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied pytest-dev/pytest repository. Pytest can generate JUnit XML reports with a `testsuite` element containing attributes such as test counts and elapsed time. I need the generated report to include the hostname attribute on that element.
Preserve existing behavior outside the changes currently requested.

Please include the hostname as an attribute on the `testsuite` element in generated JUnit XML reports.

**U1**

Please also include the timestamp as an attribute on the `testsuite` element in generated JUnit XML reports.

Update the supplied pytest-dev/pytest repository to meet these requirements:
- Generated JUnit XML reports should include the hostname as an attribute on the testsuite element.
- Generated JUnit XML reports should include the timestamp as an attribute on the testsuite element.
Preserve unrelated existing behavior.

## pytest-dev__pytest-7432.source.v1.4378479208

Class: `clarification`; updates: `clarification -> clarification`.

**U0**

Work in the supplied pytest-dev/pytest repository. pytest's skip reporting produces a location for skipped tests. The issue concerns how that location is reported when pytest runs with --runxfail.

Please preserve existing behavior outside the changes requested. I’m not yet sure how `--runxfail` should affect the reported location for tests skipped with `pytest.mark.skip` or `pytest.mark.skipif`.

**U1**

For tests skipped with `pytest.mark.skip`, `--runxfail` should leave the reported skip location at the test item itself. The behavior for `pytest.mark.skipif` remains an open question.

**U2**

For tests skipped with `pytest.mark.skipif`, `--runxfail` should also leave the reported skip location at the test item itself.

Update the supplied pytest-dev/pytest repository to meet these requirements:
- When a test is skipped by a pytest.mark.skip mark, --runxfail must not change the reported skip location from the item itself.
- When a test is skipped by a pytest.mark.skipif mark, --runxfail must not change the reported skip location from the item itself.
Preserve unrelated existing behavior.

## pytest-dev__pytest-8365.source.v1.a0504fd0a6

Class: `cumulative`; updates: `addition -> addition`.

**U0**

Work in the supplied pytest-dev/pytest repository. pytest's temporary-directory fixtures and factories derive basetemp paths using the current username. What should happen when that username contains characters that cause directory creation to fail?

Please investigate how `tmpdir` derives its basetemp path from `getpass.getuser()`. I’m not sure what change is needed, but temporary directory creation should keep working when the username contains characters that are invalid in directory names. Preserve unrelated behavior.

**U1**

Also make sure `tmpdir_factory` can create temporary directories when `getpass.getuser()` returns a username with characters invalid in directory names, including in its basetemp path. Keep the `tmpdir` requirement and preserve unrelated behavior.

**U2**

Extend the same behavior to `tmp_path_factory`: temporary directory creation must work when `getpass.getuser()` returns a username with characters invalid in directory names. Keep the `tmpdir` and `tmpdir_factory` requirements.

Update the supplied pytest-dev/pytest repository to meet these requirements:
- When the username returned by getpass.getuser() contains characters invalid for directory names, tmpdir must still allow temporary directory creation without failing because of those characters in its basetemp path.
- When the username returned by getpass.getuser() contains characters invalid for directory names, tmpdir_factory must still allow temporary directory creation without failing because of those characters in its basetemp path.
- When the username returned by getpass.getuser() contains characters invalid for directory names, tmp_path_factory must still allow temporary directory creation without failing because of those characters in its basetemp path.
Preserve unrelated existing behavior.

## pytest-dev__pytest-8906.source.v1.43303e7311

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied pytest-dev/pytest repository. I conditionally skip a test module before importing code that uses newer Python syntax. Calling `skip()` without an option raises an error whose guidance does not explain how to skip the module before that import.
Preserve existing behavior outside the changes currently requested.

I need the error guidance for calling `skip()` without an option to explain how to skip a module before Python processes newer syntax in its imports. What should it say?

**U1**

Please update the error message to explain that `skip()` can be used at module level with `allow_module_level=True`.

Update the supplied pytest-dev/pytest repository to meet these requirements:
- Explain in the error message that `skip()` can be used at module level with `allow_module_level=True`.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-10297.source.v1.1162a5951a

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. RidgeClassifierCV selects ridge classifier models across alpha values and can expose cross-validation values. Its API and resulting attribute behavior are the focus.

Add a boolean `store_cv_values` parameter to `RidgeClassifierCV`, preserving behavior outside this change. When the option is enabled with `cv=None`, what values should it retain, and what shape should they have?

**U1**

Clarification: with `store_cv_values=True` and `cv=None`, retain the cross-validation values in `cv_values_`, shaped `[n_samples, n_alphas]` or `[n_samples, n_responses, n_alphas]`.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- RidgeClassifierCV must accept a boolean `store_cv_values` parameter.
- When `store_cv_values=True` and `cv=None`, RidgeClassifierCV must retain cross-validation values in `cv_values_`, shaped `[n_samples, n_alphas]` or `[n_samples, n_responses, n_alphas]`.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-13779.source.v1.606a5ca506

Class: `mixed`; updates: `addition -> clarification`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. The component is voting estimators; the operation is fitting with sample weights.

Please preserve existing behavior outside the requested changes. Should this also cover handling estimators set to None when fitting a VotingClassifier with sample weights?

**U1**

Also handle estimators set to None when fitting other supported voting estimators with sample weights, without raising an AttributeError from trying to call fit on None. Should this also cover VotingClassifier?

**U2**

Yes, include VotingClassifier: when fitting it with sample weights, handle estimators set to None without raising an AttributeError from trying to call fit on None.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- When fitting a VotingClassifier with sample weights, handle estimators set to None without raising an AttributeError by attempting to call fit on None.
- When fitting all other supported voting estimators with sample weights, handle estimators set to None without raising an AttributeError by attempting to call fit on None.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-14087.source.v1.7d58a86d6b

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. Adjust LogisticRegressionCV fitting behavior when estimating regularization through cross-validation.

Please preserve existing behavior outside the changes requested. I’m not sure what should happen when LogisticRegressionCV estimates regularization through cross-validation with refit disabled.

**U1**

Please allow LogisticRegressionCV to estimate a regularization parameter via cross-validation with refit=False without raising an indexing error.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- Allow LogisticRegressionCV to estimate a regularization parameter via cross-validation with refit=False without raising an indexing error.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-14983.source.v1.b98dce40ff

Class: `clarification`; updates: `clarification -> clarification`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. The scikit-learn model selection API has repeated cross-validation splitters whose object representations can be specified.

Please update the repeated cross-validation splitters’ repr() behavior while preserving unrelated behavior. I’m not sure what RepeatedKFold or RepeatedStratifiedKFold should display yet.

**U1**

Clarifying one point: RepeatedKFold’s repr() should show its class name and parameter values, including n_splits, n_repeats, and random_state. The display for RepeatedStratifiedKFold is still open.

**U2**

Also, RepeatedStratifiedKFold’s repr() should show its class name and parameter values, including n_splits, n_repeats, and random_state.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- repr() of RepeatedKFold should display its class name and parameter values, including n_splits, n_repeats, and random_state.
- repr() of RepeatedStratifiedKFold should display its class name and parameter values, including n_splits, n_repeats, and random_state.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-25500.source.v1.d2f4b2717c

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. In scikit-learn, CalibratedClassifierCV with method='isotonic' encounters a shape mismatch during prediction when the global setting is set_config(transform_output="pandas"). The internal isotonic calibrator returns a DataFrame that cannot be assigned into the probability array column.
Preserve existing behavior outside the changes currently requested.

When CalibratedClassifierCV uses isotonic regression with transform_output="pandas", reject fitting with a clear ValueError explaining that this configuration is unsupported.

**U1**

Replace the fit-time rejection requirement: CalibratedClassifierCV using isotonic regression should work with transform_output="pandas" without crashing during prediction.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- Ensure CalibratedClassifierCV using isotonic regression can be used with transform_output="pandas" without crashing during prediction.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-25570.source.v1.034f367054

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. In scikit-learn, `ColumnTransformer` can be configured with transformers that select columns by name, and pipelines can request pandas output with `set_output(transform="pandas")`. How should `ColumnTransformer` behave when a transformer selects no features under pandas output?
Preserve existing behavior outside the changes currently requested.

How should `ColumnTransformer` behave when pandas output is enabled and a transformer selects no features: should that configuration be rejected, or should the empty transformer step be ignored?

**U1**

When pandas output is enabled, reject a `ColumnTransformer` configuration if any transformer selects zero features.

**U2**

I’ve changed the requirement: when using pandas output, ignore a `ColumnTransformer` step that selects zero features so it does not cause output assembly to fail.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- When using pandas output, ignore a ColumnTransformer step that selects zero features so it does not cause output assembly to fail.
Preserve unrelated existing behavior.

## scikit-learn__scikit-learn-25638.source.v1.a4fa121044

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied scikit-learn/scikit-learn repository. `sklearn.utils.multiclass.unique_labels` accepts label collections and determines their label types. I’m evaluating its behavior when inputs use pandas nullable dtypes.
Preserve existing behavior outside the changes currently requested.

Please keep `unique_labels` rejecting pandas nullable `Int64`, `Float64`, and `boolean` inputs with the mixed-type `ValueError`, so callers must convert them before use.

**U1**

Change that requirement: please make `unique_labels` accept pandas nullable `Int64`, `Float64`, and `boolean` inputs without the mixed-type `ValueError`, matching the no-error behavior for the corresponding `int64`, `float64`, and `bool` inputs.

Update the supplied scikit-learn/scikit-learn repository to meet these requirements:
- Make unique_labels accept pandas nullable Int64, Float64, and boolean inputs without raising the mixed-type ValueError, matching the no-error behavior for the corresponding int64, float64, and bool inputs.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-11445.source.v1.d6bc64987d

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. This concerns Sphinx document parsing when rst_prolog is configured and a document begins with a heading that uses a domain role. What handling should that heading receive?

I’ll preserve existing behavior outside the requested changes. When `rst_prolog` is configured, what should happen to a document’s first heading if it contains a domain role?

**U1**

Please correctly render the first heading containing a domain role when `rst_prolog` is set, and include it in the toctree.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- When rst_prolog is set, correctly render a document’s first heading containing a domain role and include the heading in the toctree.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-7738.source.v1.6dc9ccb8e0

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. Adjust Sphinx Napoleon attribute documentation rendering.

I’m adjusting Napoleon’s attribute documentation rendering while preserving unrelated behavior. What should rendered attribute names look like when they end in an underscore?

**U1**

For attribute names ending in an underscore, HTML output should not show a backslash before the underscore. Please keep unrelated behavior unchanged.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- When Napoleon renders an attribute name ending in an underscore, HTML output must not show a backslash before that underscore.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-7975.source.v1.196859cbd7

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. I’m working on how Sphinx builds the HTML index: it groups entries under headings and creates links to those sections.
Preserve existing behavior outside the changes currently requested.

In the HTML index, keep entries beginning with different symbol characters in separate Symbols sections, with each section link targeting its own section.

**U1**

Change that requirement: entries beginning with @, £, or ← should appear together in one Symbols section, and the Symbols link should target that section.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- In HTML index output, entries beginning with @, £, or ← must appear together in one Symbols section, and the Symbols link must target that section.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-8282.source.v1.aadc23eb03

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. Sphinx autodoc renders overloaded callables from Python API documentation. How should type hints be handled in that rendering?
Preserve existing behavior outside the changes currently requested.

For overloaded callables, how should parameter and return type hints be displayed? Should they follow the same policy or be handled independently?

**U1**

For overloaded callables, hide parameter type hints while retaining return type hints.

**U2**

Change the policy for overloaded callables: apply the configured `autodoc_typehints` behavior to both parameter and return type hints.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- Apply the configured autodoc_typehints behavior to parameter and return type hints for overloaded callables.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-8435.source.v1.204a2e381b

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. I’m using Sphinx autodoc with `autodoc_type_aliases` to render annotations for documented variables and attributes. The alias mapping and members are configured in the documentation build.
Preserve existing behavior outside the changes currently requested.

Please apply entries in `autodoc_type_aliases` to annotations of documented module-level variables.

**U1**

Also apply entries in `autodoc_type_aliases` to annotations of documented class attributes.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- Apply entries in autodoc_type_aliases to the annotations of documented module-level variables.
- Apply entries in autodoc_type_aliases to the annotations of documented class attributes.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-8595.source.v1.edef33284e

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. I’m documenting a Python package with Sphinx autodoc. An `automodule` directive with `:members:` controls which module members appear in the generated documentation.
Preserve existing behavior outside the changes currently requested.

For an `automodule` with `:members:`, if the module defines an empty `__all__`, treat it as absent and show the members.

**U1**

Correction: for an `automodule` with `:members:`, if the module defines an empty `__all__`, show no entries.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- When autodoc processes an automodule with :members: and the module defines an empty __all__, show no entries.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-8627.source.v1.2e357f0e88

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. Adjust Sphinx autodoc type annotation reference resolution.

Please preserve existing behavior outside the changes requested. Which type annotation references should autodoc resolve?

**U1**

Please update autodoc to resolve struct.Struct references in type annotations and document them correctly, consistently with the resolving behavior for pathlib.Path. Preserve existing behavior outside these changes.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- Sphinx autodoc must resolve references to struct.Struct when it appears in type annotations.
- Resolved struct.Struct type annotations should be documented correctly, consistently with the resolving behavior described for pathlib.Path.
Preserve unrelated existing behavior.

## sphinx-doc__sphinx-8721.source.v1.16bdc2c545

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sphinx-doc/sphinx repository. Adjust how the viewcode extension creates module pages during HTML and EPUB builds.

Please adjust how the viewcode extension creates module pages during HTML and EPUB builds. Preserve existing behavior outside the requested change. I’m unsure what `viewcode_enable_epub=False` should mean for EPUB module pages when both builders run together.

**U1**

When `viewcode_enable_epub=False`, viewcode must not create module pages for EPUB during a combined HTML and EPUB build. Keep unrelated existing behavior unchanged.

Update the supplied sphinx-doc/sphinx repository to meet these requirements:
- When `viewcode_enable_epub=False`, viewcode must not create module pages for EPUB during a combined HTML and EPUB build.
Preserve unrelated existing behavior.

## sympy__sympy-12236.source.v1.ca540bcbfd

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's apart operation decomposes rational expressions with respect to a generator. The reported issue shows a discrepancy between the result for an expression containing a symbolic coefficient and the result after substituting that coefficient.
Preserve existing behavior outside the changes currently requested.

Should `apart(t)` preserve the value of the reported expression when decomposing it?

**U1**

For `bug = a * (-t + (-t + 1) * (2 * t - 1)) / (2 * t - 1)`, where `a` is real and `t` is real and nonnegative, `bug.apart(t)` should return a decomposition equivalent to `bug`, preserving its rational-expression value instead of returning only `-a*t`.

Update the supplied sympy/sympy repository to meet these requirements:
- For `bug = a * (-t + (-t + 1) * (2 * t - 1)) / (2 * t - 1)` with real `a` and real nonnegative `t`, `bug.apart(t)` must return a decomposition equivalent to `bug`, preserving its value as a rational expression instead of returning only `-a*t`.
Preserve unrelated existing behavior.

## sympy__sympy-12481.source.v1.dde71f129c

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, the `Permutation` constructor accepts cycles as input. I want overlapping cycles rejected with a clear `ValueError`, since that policy makes ambiguous input explicit.
Preserve existing behavior outside the changes currently requested.

Please make the `Permutation` constructor reject non-disjoint supplied cycles with a clear `ValueError`.

**U1**

Change that policy: when supplied cycles overlap, apply them in left-to-right order and return the resulting permutation.

Update the supplied sympy/sympy repository to meet these requirements:
- When the supplied cycles are non-disjoint, apply them in left-to-right order and return the resulting permutation.
Preserve unrelated existing behavior.

## sympy__sympy-13773.source.v1.0d4a98ab20

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, `__matmul__` implements the `@` operator for matrix objects. The issue notes that its current behavior copies `__mul__`, while NumPy treats `@` as matrix multiplication.
Preserve existing behavior outside the changes currently requested.

Please allow scalar operands with `@` on matrices, preserving the current scalar multiplication behavior.

**U1**

Please revise that requirement: `@` should work only when both operands are matrices, and should fail if either operand is not a matrix.

Update the supplied sympy/sympy repository to meet these requirements:
- The `@` operator (`__matmul__`) must only work when both operands are matrices; it must fail if either operand is not a matrix.
Preserve unrelated existing behavior.

## sympy__sympy-14308.source.v1.a817b5439e

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's vector module pretty prints expressions that combine scalar expressions with Cartesian basis vectors. The reported output for a symbolic power of a ratio multiplied by a basis vector has a malformed layout.
Preserve existing behavior outside the changes currently requested.

Please fix the malformed duplicated layout when pretty-printing a symbolic power of a ratio multiplied by a Cartesian basis vector.

**U1**

Also center the baseline when printing vector expressions.

Update the supplied sympy/sympy repository to meet these requirements:
- Pretty printing vector expressions must render correctly without the duplicated or malformed layout shown for a symbolic power of a ratio multiplied by a Cartesian basis vector.
- When vector expressions print correctly, their baseline must be centered.
Preserve unrelated existing behavior.

## sympy__sympy-14317.source.v1.526d973f83

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's LaTeX printer renders `Poly` expressions, including their monomials and generator. The issue reports that its displayed term order differs from the order used by `str` and `pretty`.
Preserve existing behavior outside the changes currently requested.

Please arrange Poly monomials in LaTeX in ascending degree order for readability in rendered equations.

**U1**

Change that requirement: print Poly monomials in LaTeX from highest to lowest degree, matching the logical order used by str and pretty.

Update the supplied sympy/sympy repository to meet these requirements:
- Print Poly monomials in LaTeX in the same logical order as str and pretty: from highest to lowest degree.
Preserve unrelated existing behavior.

## sympy__sympy-14396.source.v1.b79ea37a37

Class: `clarification`; updates: `clarification`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, Poly(1.2*x*y*z, x) infers domain='RR[y,z]', but explicitly passing that same domain to Poly(1.2*x*y*z, x, domain='RR[y,z]') raises OptionError.
Preserve existing behavior outside the changes currently requested.

I'm not yet sure how Poly should behave when domain='RR[y,z]' is supplied explicitly for this expression.

**U1**

Please allow domain specifications of the form RR[y,z] for this case, so Poly(1.2*x*y*z, x, domain='RR[y,z]') succeeds.

Update the supplied sympy/sympy repository to meet these requirements:
- Allow Poly to accept domain specifications of the form RR[y,z] for the illustrated case, so Poly(1.2*x*y*z, x, domain='RR[y,z]') succeeds.
Preserve unrelated existing behavior.

## sympy__sympy-14774.source.v1.b324ec158f

Class: `mixed`; updates: `addition -> clarification`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's LaTeX printer supports an inv_trig_style option. With inv_trig_style="full", acsc(x) currently prints with the function name acsc. I want to address full-name printing for reciprocal inverse trigonometric functions.
Preserve existing behavior outside the changes currently requested.

Please investigate full-name printing for acsc(x). What function name and LaTeX output should it use when inv_trig_style="full"?

**U1**

Also, when inv_trig_style="full", asec must render using the full name arcsec.

**U2**

For acsc, use the full name arccsc when inv_trig_style="full". The output for acsc(x) must match the Python string representation '\\operatorname{arccsc}{\\left (x \\right )}'.

Update the supplied sympy/sympy repository to meet these requirements:
- When inv_trig_style="full", the LaTeX printer must render acsc using the full name arccsc, including producing '\\operatorname{arccsc}{\\left (x \\right )}' for acsc(x).
- When inv_trig_style="full", the LaTeX printer must render asec using the full name arcsec.
Preserve unrelated existing behavior.

## sympy__sympy-14817.source.v1.8d3cf61cea

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's MatAdd pretty printer encounters MatrixSymbol names stored as strings. Pretty printing MatrixSymbol('x', n, n) + MatrixSymbol('y*', n, n) currently raises a SympifyError while processing the name 'y*'.
Preserve existing behavior outside the changes currently requested.

When pretty printing MatAdd, explicitly reject MatrixSymbol names that are not plain identifiers with a clear validation error, so operator-like labels cannot produce ambiguous output.

**U1**

Replace the name-validation requirement: instead of rejecting names that are not plain identifiers, make MatAdd pretty printing handle MatrixSymbol string arguments without passing them to sympify, so names such as `y*` print without the reported error.

Update the supplied sympy/sympy repository to meet these requirements:
- Make MatAdd pretty printing handle MatrixSymbol string arguments without passing them to sympify, so symbols with names such as `y*` can be printed without the reported error.
Preserve unrelated existing behavior.

## sympy__sympy-15011.source.v1.1317fb691a

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, lambdify raises SyntaxError when a MatrixSymbol named "{v}" is used as both its argument and expression, including when dummify=True. Scalar symbols with braces and MatrixSymbols with ordinary names already work. Investigate how lambdify handles these MatrixSymbol argument names.
Preserve existing behavior outside the changes currently requested.

I'm not sure whether MatrixSymbol arguments with brace-containing names should be explicitly rejected or supported through safe generated argument names.

**U1**

Reject MatrixSymbol arguments whose names contain curly braces with a clear ValueError, including with dummify=True, before generating Python code.

**U2**

Replace the ValueError policy: make lambdify support MatrixSymbols whose names contain curly braces when used as both the input and expression, without raising a SyntaxError, including with dummify=True.

Update the supplied sympy/sympy repository to meet these requirements:
- Make lambdify handle MatrixSymbols whose names contain curly braces when used as both the input and expression, without raising a SyntaxError, including with dummify=True.
Preserve unrelated existing behavior.

## sympy__sympy-15308.source.v1.2e3de89bf6

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy/sympy, with A = MatrixSymbol("A", n, n), latex(trace(A**2)) currently returns 'Trace(A**2)'. Matrix traces therefore appear as raw expression text in generated mathematical documents.
Preserve existing behavior outside the changes currently requested.

Please investigate how LaTeX printing should handle matrix trace expressions. I'm unsure whether it should explicitly reject them or render them as mathematical LaTeX.

**U1**

Make LaTeX printing explicitly reject matrix trace expressions with an unsupported-expression error.

**U2**

Replace the rejection behavior with LaTeX rendering for matrix trace expressions. Use LaTeX printing for the enclosed expression so that powers appear as A^2 rather than A**2.

Update the supplied sympy/sympy repository to meet these requirements:
- Render matrix trace expressions in LaTeX, using LaTeX printing for the enclosed expression so that powers appear as A^2 rather than A**2.
Preserve unrelated existing behavior.

## sympy__sympy-15346.source.v1.16243e29b2

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, simplify() combines sin(x)*sin(y) + cos(x)*cos(y) for symbolic arguments, but leaves the corresponding expression with exact Rational arguments unchanged. This occurs both when constructing the expression directly and when taking a matrix dot product.
Preserve existing behavior outside the changes currently requested.

Make simplify() apply sin(a)*sin(b) + cos(a)*cos(b) = cos(a - b) for exact Rational arguments, both in directly constructed expressions and in expressions produced by matrix dot products. For arguments 1/50 and 1/25, the result should be cos(1/50).

**U1**

Also make simplify() handle acos applied to these rational-argument trigonometric expressions, returning the exact resulting angle where permitted by the principal range of acos. For the expression with arguments 1/50 and 1/25, applying acos should simplify to 1/50.

Update the supplied sympy/sympy repository to meet these requirements:
- Make simplify() apply the identity sin(a)*sin(b) + cos(a)*cos(b) = cos(a - b) for rational arguments, including expressions constructed directly or produced by matrix dot products. The reported arguments 1/50 and 1/25 should yield cos(1/50).
- Make simplify() simplify acos applied to these rational-argument trigonometric expressions to the exact resulting angle where permitted by the principal range of acos; the reported expression should yield 1/50.
Preserve unrelated existing behavior.

## sympy__sympy-15609.source.v1.85ef08dfb9

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, evaluating latex((M*N)[i, j]) with i, j, k = symbols("i j k") and M and N both MatrixSymbol objects of shape (k, k) produces \sum_{i_{1}=0}^{k - 1} M_{i, _i_1} N_{_i_1, j}. The generated summation index causes double-subscript errors in LaTeX and prevents MathJax rendering. Address how the indexed matrix-expression printer handles this situation.
Preserve existing behavior outside the changes currently requested.

Please investigate the affected indexed matrix expressions. I'm unsure whether printing should reject them explicitly or produce valid LaTeX that also renders in MathJax.

**U1**

When a generated summation-index name would cause double-subscript errors in an indexed matrix expression, reject LaTeX printing with a clear error rather than returning the malformed string.

**U2**

Replace the rejection policy with printing indexed matrix expressions using valid summation-index subscripts, avoiding double-subscript errors so the output compiles in LaTeX and renders in MathJax.

Update the supplied sympy/sympy repository to meet these requirements:
- Print indexed matrix expressions with valid summation-index subscripts, avoiding double-subscript errors so the output compiles in LaTeX and renders in MathJax.
Preserve unrelated existing behavior.

## sympy__sympy-16503.source.v1.6b6511c410

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's pretty printer displays a summand and an outside additive term at different heights in expressions such as Sum(x, (x, 1, oo)) + 3. Tall summation notation makes these additions awkward to read in terminal output.
Preserve existing behavior outside the changes currently requested.

Please investigate the layout options. I'm unsure whether outside additive terms should go on a continuation line to conserve width or share a baseline with the summand when an addition contains a tall Sum.

**U1**

When pretty-printing an addition containing a Sum, put the outside additive terms on a separate continuation line below the Sum to reduce horizontal width.

**U2**

Replace the continuation-line layout with alignment on the same horizontal baseline: when pretty-printing an addition containing a Sum, align the summand and the outside additive terms.

Update the supplied sympy/sympy repository to meet these requirements:
- When pretty-printing an addition containing a Sum, align the summand and the outside additive terms on the same horizontal baseline.
Preserve unrelated existing behavior.

## sympy__sympy-16792.source.v1.94178cb91a

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's Cython autowrap can generate a scalar C parameter for an explicitly supplied MatrixSymbol array argument when the wrapped expression does not reference it. Passing a NumPy array then raises a scalar-conversion TypeError. Investigate how this unused-array situation should be handled.
Preserve existing behavior outside the changes currently requested.

Please investigate whether unused array arguments should be explicitly rejected by Cython autowrap or accepted with array-compatible signatures. I'm unsure which behavior is appropriate.

**U1**

Have Cython autowrap reject explicitly supplied array arguments that do not appear in the wrapped expression with a clear validation error.

**U2**

Replace the rejection policy with support for unused array arguments: explicitly supplied array arguments should retain array-compatible signatures even when absent from the wrapped expression, so calls with those arrays return the expression's expected result.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix Cython autowrap so explicitly supplied array arguments retain their array-compatible signatures even when absent from the wrapped expression, allowing calls with those arrays to return the expression's expected result.
Preserve unrelated existing behavior.

## sympy__sympy-17139.source.v1.8625dd4bfb

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, simplifying cos(x)**I reaches the trigonometric transformations in fu.py and raises TypeError: Invalid comparison of complex I while comparing the exponent with zero. Investigate how simplification handles trigonometric powers whose exponents are non-real.
Preserve existing behavior outside the changes currently requested.

Please investigate whether simplification should explicitly reject trigonometric powers with non-real exponents or accept them while avoiding exponent-dependent transformations that cannot safely apply. I’m unsure which behavior is appropriate.

**U1**

Simplification should explicitly reject trigonometric powers with non-real exponents, raising a deliberate TypeError explaining that these powers are unsupported.

**U2**

Remove the requirement to explicitly reject these powers. Fix simplification of trigonometric powers with non-real exponents so it does not raise an invalid-comparison TypeError when considering exponent-dependent transformations.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix simplification of trigonometric powers with non-real exponents so it does not raise an invalid-comparison TypeError when considering exponent-dependent transformations.
Preserve unrelated existing behavior.

## sympy__sympy-17630.source.v1.4793bc0af1

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, let a = MatrixSymbol("a", 2, 2), z = ZeroMatrix(2, 2), and b = BlockMatrix([[a, z], [z, z]]). block_collapse(b * b) succeeds, but block_collapse(b * b * b) raises AttributeError: 'Zero' object has no attribute 'cols'. Fix block_collapse so repeated products of compatible block matrices containing ZeroMatrix blocks evaluate correctly.
Preserve existing behavior outside the changes currently requested.

Please investigate what causes the failure in the example and fix it.

**U1**

Also ensure that direct BlockMatrix._blockmul preserves zero blocks as appropriately dimensioned ZeroMatrix objects rather than scalar Zero objects, so its results can participate correctly in further block multiplication.

Update the supplied sympy/sympy repository to meet these requirements:
- Make block_collapse correctly evaluate repeated products of compatible block matrices containing ZeroMatrix blocks without raising an exception.
- Ensure direct BlockMatrix._blockmul preserves zero blocks as appropriately dimensioned ZeroMatrix objects rather than scalar Zero objects, allowing its results to participate correctly in further block multiplication.
Preserve unrelated existing behavior.

## sympy__sympy-17655.source.v1.10abfe00b8

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy geometry, with point1 = Point(0, 0) and point2 = Point(1, 1), point1 + point2 * sympy.sympify(2.0) works. Reversing the multiplication operands produces a symbolic Mul, and adding it to point1 raises GeometryError. Investigate how geometry.Point handles numeric multiplication on the left.
Preserve existing behavior outside the changes currently requested.

Please investigate whether numeric scalar multiplication on the left should be rejected immediately or should scale the point just like multiplication on the right. I'm unsure which behavior is intended.

**U1**

Numeric scalar multiplication on the left of geometry.Point should immediately raise TypeError rather than construct a symbolic product.

**U2**

Replace the earlier TypeError policy with consistent numeric scalar multiplication of geometry.Point across both operand orders, so adding the scaled point to another point gives the same result without an exception.

Update the supplied sympy/sympy repository to meet these requirements:
- Make numeric scalar multiplication of geometry.Point consistent across operand orders, so adding the scaled point to another point gives the same result without an exception.
Preserve unrelated existing behavior.

## sympy__sympy-18057.source.v1.6de91aea63

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy equality comparisons can send an unknown object's representation through expression parsing. For example, comparing Symbol('x') with an object whose repr is 'x.y' reaches eval and raises AttributeError. This affects comparisons involving custom objects in mixed collections.
Preserve existing behavior outside the changes currently requested.

Please investigate how equality should handle unknown operands. Should it explicitly raise TypeError, or allow the comparison to complete without interpreting their representations?

**U1**

Equality should explicitly raise TypeError when it encounters an unknown object, without interpreting its representation.

**U2**

Replace the explicit TypeError requirement with handling that lets equality comparisons with unknown objects complete without interpreting their representations as expressions, preventing evaluation-induced exceptions and false equality with symbols.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix SymPy equality comparisons with unknown objects so their representations are not interpreted as expressions, preventing evaluation-induced exceptions and false equality with symbols.
Preserve unrelated existing behavior.

## sympy__sympy-18087.source.v1.ee4657029a

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. I am writing SymPy-based teaching material and found that trigsimp handles cos(x)+sqrt(sin(x)**2) incorrectly for general complex x, although the real-x case behaves correctly. Please investigate how it handles this expression when x is not known to be real.
Preserve existing behavior outside the changes currently requested.

For expressions containing sqrt(sin(x)**2) when x is not known to be real, should trigsimp explicitly reject the input or accept it using only transformations valid for complex arguments?

**U1**

Have trigsimp explicitly reject expressions containing sqrt(sin(x)**2) when x is not known to be real, so my teaching material fails visibly on unsupported arguments.

**U2**

Replace the earlier request for explicit rejection with a fix that keeps simplification of trigonometric expressions containing square roots of squared sine terms valid for general complex arguments. Do not assume sqrt(sin(x)**2) equals sin(x).

Update the supplied sympy/sympy repository to meet these requirements:
- Correct trigsimp so that simplifying trigonometric expressions with square roots of squared sine terms remains valid for general complex arguments, without assuming sqrt(sin(x)**2) equals sin(x).
Preserve unrelated existing behavior.

## sympy__sympy-18189.source.v1.bb929d34f3

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's diophantine returns eight solutions for n**4 + m**4 - 2**4 - 3**4 with syms=(m,n), permute=True, but only {(3, 2)} with syms=(n,m). Investigate how permute=True handles explicit symbol ordering; we need to decide how the API should handle orders that differ from its default.
Preserve existing behavior outside the changes currently requested.

Please investigate the ordering discrepancy and help me decide whether permute=True should reject explicit syms orders that differ from the default or support them with complete solutions whose tuple coordinates follow the requested order.

**U1**

When permute=True, reject explicit syms orders that differ from the default symbol order with a clear error.

**U2**

Replace the rejection policy with support for any syms ordering: with permute=True, return complete solutions with tuple coordinates following the requested symbol order.

Update the supplied sympy/sympy repository to meet these requirements:
- Ensure diophantine with permute=True returns complete solutions regardless of syms ordering, with tuple coordinates following the requested symbol order.
Preserve unrelated existing behavior.

## sympy__sympy-18621.source.v1.312d5c71c7

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy/sympy, converting a BlockDiagMatrix containing one Matrix block using sympy.Matrix(D) raises TypeError: 'One' object is not subscriptable. Conversion with two blocks succeeds. The singleton case needs an intentional handling policy.
Preserve existing behavior outside the changes currently requested.

Please investigate the singleton conversion failure. I'm unsure whether conversion should deliberately reject a BlockDiagMatrix containing one Matrix block or produce a regular Matrix with that block's dimensions and entries.

**U1**

Deliberately reject conversion of a BlockDiagMatrix containing a single Matrix block, with a clear validation error explaining that at least two blocks are required.

**U2**

Change the rejection policy: allow a BlockDiagMatrix containing a single Matrix block to convert to a regular Matrix with the same dimensions and entries as that block, without raising an exception.

Update the supplied sympy/sympy repository to meet these requirements:
- Allow a BlockDiagMatrix containing a single Matrix block to convert to a regular Matrix with the same dimensions and entries as that block, without raising an exception.
Preserve unrelated existing behavior.

## sympy__sympy-18698.source.v1.7f4b32d8ef

Class: `cumulative`; updates: `addition`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, sqf_list can return separate factors with the same multiplicity. For example, (x**2 + 1)*(x - 1)**2*(x - 2)**3*(x - 3)**3 produces separate entries for x - 2 and x - 3, both with multiplicity 3.
Preserve existing behavior outside the changes currently requested.

Make sqf_list combine factors with the same multiplicity into a single square-free factor paired with that multiplicity.

**U1**

Make sqf combine factors with equal multiplicity too, consistently with sqf_list.

Update the supplied sympy/sympy repository to meet these requirements:
- Make sqf_list combine factors with the same multiplicity into a single square-free factor paired with that multiplicity.
- Make sqf follow the same rule of combining factors with equal multiplicity, consistently with sqf_list.
Preserve unrelated existing behavior.

## sympy__sympy-19007.source.v1.d13eaced17

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, consider A = MatrixSymbol('A', 1, 1), B = MatrixSymbol('B', n, 1), and C = BlockMatrix([[A], [B]]), with integer symbols n and i. Accessing C[i, 0] currently produces A[i, 0], although the symbolic row index does not establish which block contains the element. Investigate how BlockMatrix indexing handles this ambiguity.
Preserve existing behavior outside the changes currently requested.

Please check whether an access whose symbolic index does not determine the containing block should be rejected or preserved as an unresolved symbolic element.

**U1**

Reject the access with an explicit error when its symbolic index does not determine which block contains the element.

**U2**

Replace that error policy with preserving the BlockMatrix element access without simplifying it to a particular block when the symbolic index does not determine which block contains the element.

Update the supplied sympy/sympy repository to meet these requirements:
- Preserve a BlockMatrix element access without simplifying it to a particular block when the symbolic index does not determine which block contains the element.
Preserve unrelated existing behavior.

## sympy__sympy-20154.source.v1.d0295bcf19

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. The partitions() iterator in sympy.utilities.iterables yields dictionaries representing partitions. Consumers may process each result immediately or retain results for later use, so dictionary ownership and allocation costs matter.
Preserve existing behavior outside the changes currently requested.

Please investigate the dictionary ownership tradeoff. I’m unsure whether results should use a reusable dictionary for immediate consumption or independent dictionaries that callers can retain.

**U1**

Keep yielding a reusable dictionary to prioritize low allocation costs for callers processing each partition immediately. Explicitly document that the yielded dictionary’s lifetime ends when iteration advances.

**U2**

Replace the earlier reusable-dictionary policy with independent dictionaries. Continuing iteration must not change previously yielded partitions, including when collecting the iterator into a list.

Update the supplied sympy/sympy repository to meet these requirements:
- Make partitions() yield independent dictionaries so that continuing iteration does not change previously yielded partitions, including when collecting the iterator into a list.
Preserve unrelated existing behavior.

## sympy__sympy-20212.source.v1.1ff8c46f32

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy 1.5.1, evaluating `0**-oo` returns `0`. Investigate how Pow handles this singular expression and establish an intentional evaluation policy.
Preserve existing behavior outside the changes currently requested.

Please assess whether `0**-oo` should raise an exception or produce a symbolic result; I'm unsure which policy is appropriate.

**U1**

Have `0**-oo` raise ValueError so this singular expression cannot silently enter further calculations.

**U2**

Replace the ValueError policy with evaluation to ComplexInfinity (`zoo`) for `0**-oo`, as documented.

Update the supplied sympy/sympy repository to meet these requirements:
- Make zero raised to negative infinity (`0**-oo`) evaluate to ComplexInfinity (`zoo`) as documented.
Preserve unrelated existing behavior.

## sympy__sympy-20322.source.v1.67cb5df725

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy 1.6.2, simplifying sympify('4*ceiling(x/4 - 3/4)', evaluate=False) produces 4*ceiling(x/4) - 3, while parsing with evaluate=True preserves 4*ceiling(x/4 - 3/4). This raises a correctness issue when parsing ceiling expressions without evaluation.
Preserve existing behavior outside the changes currently requested.

Please investigate the discrepancy. I'm unsure whether sympify should reject ceiling expressions when evaluate=False as a correctness safeguard, or support them with mathematically correct simplification consistent with evaluate=True.

**U1**

Reject ceiling expressions passed to sympify with evaluate=False with a clear error, preventing them from reaching potentially incorrect simplification.

**U2**

Replace the rejection policy with support for ceiling expressions parsed by sympify with evaluate=False, ensuring their simplification is mathematically correct and consistent with parsing with evaluate=True.

Update the supplied sympy/sympy repository to meet these requirements:
- Ensure that simplifying ceiling expressions parsed by sympify with evaluate=False is mathematically correct and consistent with parsing with evaluate=True.
Preserve unrelated existing behavior.

## sympy__sympy-20590.source.v1.74d1407c82

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. I'm reviewing instance storage for sympy.Symbol following the change from 1.6.2 to 1.7. The presence of an instance dictionary affects both attaching metadata to symbols and memory use in large symbolic workloads.
Preserve existing behavior outside the changes currently requested.

Please investigate Symbol's instance storage. I'm unsure whether instances should retain a __dict__ for extra metadata or enforce slotted storage with no __dict__ attribute.

**U1**

Retain an instance __dict__ on Symbol objects so callers can attach extra per-instance metadata.

**U2**

Replace the requirement to retain an instance dictionary with restoring Symbol instances' slotted behavior: they should have no __dict__ attribute, and accessing it should raise AttributeError.

Update the supplied sympy/sympy repository to meet these requirements:
- Restore Symbol instances' slotted behavior so they have no __dict__ attribute and accessing it raises AttributeError.
Preserve unrelated existing behavior.

## sympy__sympy-20639.source.v1.c4904546c8

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, pretty-printing pi**(1/E) currently shows a radical with index -1. The LaTeX and string representations accurately retain the exponent. Please investigate how the pretty printer handles this reciprocal-E exponent.
Preserve existing behavior outside the changes currently requested.

I'm unsure whether powers with reciprocal-E exponents should produce a clear unsupported-formatting error or support an accurate mathematical display. Please investigate which approach is appropriate.

**U1**

For powers with reciprocal-E exponents, have the pretty printer raise a clear unsupported-formatting error rather than render the expression.

**U2**

Replace the error behavior with accurate pretty-printing of powers with reciprocal-E exponents. For example, pi**(1/E) should accurately represent its exponent rather than display a radical with index -1.

Update the supplied sympy/sympy repository to meet these requirements:
- Correct pretty-printing of powers with reciprocal-E exponents, exemplified by pi**(1/E), so they accurately represent the exponent instead of displaying a radical with index -1.
Preserve unrelated existing behavior.

## sympy__sympy-21055.source.v1.f1e1b374fc

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, refining arg(a) with Q.positive(a) currently leaves arg(a) unchanged. This also leaves an argument-dependent condition in a Piecewise result from Integral(sin(x)*exp(-a*x), (x, 0, oo)) unresolved. I need a deliberate handling policy for symbolic argument expressions in this refinement workflow.
Preserve existing behavior outside the changes currently requested.

Please investigate how refine() should handle symbolic arg expressions when assumptions are supplied. I'm unsure whether it should explicitly reject them or simplify them when the assumptions determine the argument.

**U1**

Have refine() raise an explicit error when it encounters a symbolic arg expression with supplied assumptions, rather than attempting assumption-based argument simplification. This should also apply when the assumptions assert positivity.

**U2**

Replace the error policy with simplification under real-number assumptions that determine the complex argument's value. In particular, refine() should reduce arg(a) to zero under Q.positive(a), allowing enclosing conditions and Piecewise expressions to simplify accordingly.

Update the supplied sympy/sympy repository to meet these requirements:
- Make refine() simplify complex argument expressions under real-number assumptions that determine their values, including reducing arg(a) to zero under Q.positive(a), so enclosing conditions and Piecewise expressions simplify accordingly.
Preserve unrelated existing behavior.

## sympy__sympy-21171.source.v1.81176d29ad

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's LaTeX printer fails when displaying powers of SingularityFunction expressions. This appears in Jupyter rich display of the shear-force expression from a Beam with an applied load and fixed support.
Preserve existing behavior outside the changes currently requested.

Please investigate the display failure. I'm unsure whether expressions containing powers of SingularityFunction should use a plain-text fallback in notebooks or support proper LaTeX rendering.

**U1**

Use a plain-text fallback for expressions containing powers of SingularityFunction so their notebook output remains readable.

**U2**

Replace the plain-text fallback approach with correct LaTeX rendering of powers of SingularityFunction, including Jupyter rich display, without raising the unexpected `exp` keyword argument error.

Update the supplied sympy/sympy repository to meet these requirements:
- Correctly render powers of SingularityFunction expressions in LaTeX, including Jupyter rich display, without raising the unexpected exp keyword argument error.
Preserve unrelated existing behavior.

## sympy__sympy-21379.source.v1.ccb98e621e

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, an integer-to-float casting pass uses subs({1: 1.0}) before TensorFlow lambdify. With a cleared cache, exp(sinh(Piecewise((x, y > x), (y, True)) / z)) can raise PolynomialError when x and y are real. Repeating the substitution without clearing the cache can succeed. Investigate how substitution should handle this class of expression.
Preserve existing behavior outside the changes currently requested.

Please investigate whether integer-to-float substitutions involving hyperbolic functions with Piecewise arguments should be rejected as unsupported or supported without raising PolynomialError.

**U1**

Treat these substitutions as unsupported. Deliberately reject them with a clear validation error so the casting pipeline fails predictably.

**U2**

Please replace the rejection policy with support for valid integer-to-float substitutions involving hyperbolic functions with Piecewise arguments. Fix the unexpected PolynomialError, including cases with real symbols, symbolic division, enclosing functions, and a cleared cache.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix integer-to-float substitution in expressions containing hyperbolic functions with Piecewise arguments so that valid substitutions do not raise the unexpected PolynomialError, including with real symbols, symbolic division, enclosing functions, and a cleared cache.
Preserve unrelated existing behavior.

## sympy__sympy-21614.source.v1.043d30f84f

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, an unevaluated Derivative of a matrix expression exposes kind metadata used by symbolic consumers. For A = MatrixSymbol('A', 2, 2), Derivative(A, x).kind currently returns UndefinedKind. I am investigating how this operation should handle matrix-valued operands when its kind metadata is unreliable.
Preserve existing behavior outside the changes currently requested.

Please investigate whether matrix-valued derivatives should be rejected explicitly or remain representable with the appropriate matrix kind.

**U1**

Reject construction of Derivative objects with matrix-valued expressions with a clear error, so symbolic consumers cannot receive unreliable kind metadata for those derivatives.

**U2**

Replace the rejection policy with support for representing matrix-valued derivatives. Correct Derivative.kind to report the appropriate matrix kind, including MatrixKind(NumberKind) for a MatrixSymbol, rather than UndefinedKind.

Update the supplied sympy/sympy repository to meet these requirements:
- Correct Derivative.kind for matrix-valued expressions so it reports the appropriate matrix kind, including MatrixKind(NumberKind) for a MatrixSymbol, instead of UndefinedKind.
Preserve unrelated existing behavior.

## sympy__sympy-21627.source.v1.d7bd2599ce

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy/sympy, querying expr.is_zero after expr = sympify("cosh(acos(-i + acosh(-g + i)))") raises RecursionError: maximum recursion depth exceeded while calling a Python object.
Preserve existing behavior outside the changes currently requested.

Reject construction of cosh expressions containing nested inverse functions with an explicit ValueError, treating this input pattern as unsupported.

**U1**

Replace the construction-time ValueError rejection policy with a fix to zero checking for cosh expressions containing nested inverse functions, such as cosh(acos(-i + acosh(-g + i))), so that querying is_zero does not raise a RecursionError.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix zero checking of cosh expressions with nested inverse functions, as illustrated by cosh(acos(-i + acosh(-g + i))), so that querying is_zero does not raise a RecursionError.
Preserve unrelated existing behavior.

## sympy__sympy-21847.source.v1.3725b1139e

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's itermonomials can omit mixed-variable monomials when several variables are supplied with scalar degree bounds and a positive min_degrees value.
Preserve existing behavior outside the changes currently requested.

For itermonomials calls with multiple variables, scalar degree bounds, and positive min_degrees, raise a clear ValueError explaining that this combination is unsupported so callers cannot silently receive incomplete results.

**U1**

Replace the ValueError policy with support for scalar degree bounds: return all monomials whose total degree lies inclusively between min_degrees and max_degrees, including mixed-variable monomials, both when the bounds are equal and when max_degrees exceeds min_degrees.

Update the supplied sympy/sympy repository to meet these requirements:
- Correct itermonomials with scalar degree bounds to return all monomials whose total degree lies inclusively between min_degrees and max_degrees, including mixed-variable monomials, both when the bounds are equal and when max_degrees exceeds min_degrees.
Preserve unrelated existing behavior.

## sympy__sympy-22005.source.v1.a05e82acf8

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, solve_poly_system can encounter polynomial systems that leave some specified generators unconstrained. For example, solving (y - 1,) for x and y currently returns [(1,)], which omits the free generator. This situation can arise with expression inputs and Poly inputs.
Preserve existing behavior outside the changes currently requested.

For polynomial systems with infinitely many solutions in the specified generators, return parametric solution tuples that retain unconstrained generators as free symbols. Support both expression and Poly inputs.

**U1**

Replace the parametric-solution requirement: make solve_poly_system raise NotImplementedError for polynomial systems with infinitely many solutions in the specified generators. Apply this to both expression and Poly inputs, rather than returning incomplete solution tuples.

Update the supplied sympy/sympy repository to meet these requirements:
- Make solve_poly_system raise NotImplementedError for polynomial systems with infinitely many solutions in the specified generators, including expression and Poly inputs, instead of returning incomplete solution tuples.
Preserve unrelated existing behavior.

## sympy__sympy-22714.source.v1.27ac62b00a

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy/sympy, sympifying a Point2D string inside `with sp.evaluate(False):` currently raises an imaginary-coordinate error even for integer coordinates. The same expression succeeds outside that context and with the per-call `evaluate=False` argument.
Preserve existing behavior outside the changes currently requested.

Explicitly reject sympification of Point2D expressions inside an evaluate(False) context, including expressions with real coordinates. Raise an error explaining that this operation is unsupported while global evaluation is disabled.

**U1**

Replace the rejection policy with support for sympifying Point2D expressions with valid real coordinates inside an evaluate(False) context, without incorrectly raising ValueError('Imaginary coordinates are not permitted.').

Update the supplied sympy/sympy repository to meet these requirements:
- Allow sympification of Point2D expressions with valid real coordinates inside an evaluate(False) context without incorrectly raising ValueError('Imaginary coordinates are not permitted.').
Preserve unrelated existing behavior.

## sympy__sympy-22840.source.v1.7e7248b934

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy/sympy, cse() processes expressions containing indexed MatrixSymbols, and its replacements are subsequently passed to C code generation. Whole-matrix replacements can cause generated assignments that copy the source arrays.
Preserve existing behavior outside the changes currently requested.

Have cse() introduce independent whole-matrix temporaries for indexed MatrixSymbols and redirect indexed accesses through them so downstream generated code uses its own matrix buffers.

**U1**

Replace the requirement to introduce whole-matrix temporaries with a requirement to avoid redundant replacements that merely copy entire source matrices when cse() processes indexed MatrixSymbols, while preserving the expressions' meaning.

Update the supplied sympy/sympy repository to meet these requirements:
- When processing expressions containing indexed MatrixSymbols, cse() must avoid introducing redundant replacements that merely copy the entire source matrices, while preserving the expressions' meaning.
Preserve unrelated existing behavior.

## sympy__sympy-23117.source.v1.c27f57766e

Class: `revision`; updates: `revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's Array constructor encounters an unpacking error when given an empty list. This concerns how Array construction handles input containing no elements.
Preserve existing behavior outside the changes currently requested.

Reject an empty list passed to the SymPy Array constructor with a clear validation error so missing input data is caught intentionally.

**U1**

Change the policy from rejecting an empty list to allowing it: constructing an empty SymPy Array from an empty list should succeed without raising an error.

Update the supplied sympy/sympy repository to meet these requirements:
- Allow constructing an empty SymPy Array from an empty list without raising an error.
Preserve unrelated existing behavior.

## sympy__sympy-23191.source.v1.faf18e2c54

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. Terminal pretty-printing of sympy.vector expressions can insert basis labels into multiline scalar coefficients. Expressions involving trigonometric fractions and integrals expose the problem. Investigate how the vector printer combines coefficient layouts with basis labels.
Preserve existing behavior outside the changes currently requested.

For multiline scalar coefficients, please assess whether terminal printing should use a single-line fallback or preserve the multiline coefficient layout with correctly positioned basis labels. I'm unsure which behavior is appropriate.

**U1**

Use the single-line fallback: when a sympy.vector expression has a multiline scalar coefficient, render the entire vector expression on one line in terminal pretty-printing to avoid interleaving basis labels with the coefficient.

**U2**

Please replace the single-line fallback requirement with preserving multiline scalar coefficient layouts. Position the basis unit-vector labels correctly alongside those coefficients without disrupting their layout in terminal pretty-printing.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix terminal pretty-printing of sympy.vector expressions so basis unit-vector labels are correctly positioned alongside multiline scalar coefficients without disrupting their layout.
Preserve unrelated existing behavior.

## sympy__sympy-23262.source.v1.3272973f51

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy 1.10, the Python code printer used by lambdify([], tuple([1])) generates return (1), so the generated function returns an integer. The application encounters singleton tuple outputs, and their handling during code generation needs to be addressed.
Preserve existing behavior outside the changes currently requested.

Please investigate whether singleton tuple outputs should be rejected explicitly during Python code generation or supported with their tuple return type preserved.

**U1**

Reject singleton tuple outputs during Python code generation with a clear error rather than generating a function that silently returns a scalar.

**U2**

Replace the rejection requirement with support for singleton tuples: include the trailing comma during Python code generation so lambdify-generated functions return a tuple.

Update the supplied sympy/sympy repository to meet these requirements:
- Ensure Python code generation preserves singleton tuples by including the trailing comma, so lambdify-generated functions return a tuple.
Preserve unrelated existing behavior.

## sympy__sympy-24066.source.v1.127975a98f

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy, SI._collect_factor_and_dimension processes expressions containing exponentials and physical units. For example, 100 + exp(units.second / (units.ohm * units.farad)) involves an exponential argument whose collected dimension is expressed using time, capacitance, and impedance.
Preserve existing behavior outside the changes currently requested.

Please investigate the dimension check for exponential arguments. I'm unsure whether it should require the collected dimension to equal Dimension(1) literally or also accept dimensions equivalent to dimensionless.

**U1**

Require exponential arguments to have a collected dimension literally equal to Dimension(1). Raise ValueError for other dimension representations, even when dimensional equivalence would establish that they are dimensionless.

**U2**

Replace the earlier literal-equality requirement with acceptance of exponential arguments whose dimensions are equivalent to dimensionless, so expressions containing those exponentials are processed without an erroneous dimension-mismatch ValueError.

Update the supplied sympy/sympy repository to meet these requirements:
- Make SI._collect_factor_and_dimension recognize exponential arguments whose dimensions are equivalent to dimensionless, so expressions containing those exponentials are processed without an erroneous dimension-mismatch ValueError.
Preserve unrelated existing behavior.

## sympy__sympy-24102.source.v1.442970a0c2

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In sympy.parsing.mathematica, parse_mathematica raises SyntaxError when given the Greek variable λ. Investigate how the parser handles Greek identifiers and establish an intentional handling policy for this input.
Preserve existing behavior outside the changes currently requested.

Please assess whether Greek identifiers should be accepted as symbols or deliberately rejected with a clear validation error; I'm unsure which policy is appropriate.

**U1**

Deliberately reject Greek identifiers with a clear validation error, enforcing an ASCII-only identifier policy in parse_mathematica.

**U2**

Replace the ASCII-only rejection policy with support for parsing Greek characters as symbols. Fix parse_mathematica so that λ parses without the reported SyntaxError.

Update the supplied sympy/sympy repository to meet these requirements:
- Fix parse_mathematica to parse Greek characters as symbols, including λ, without the reported SyntaxError.
Preserve unrelated existing behavior.

## sympy__sympy-24152.source.v1.97348c4229

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. SymPy's quantum TensorProduct expansion can leave additive tensor factors unexpanded when summands carry scalar coefficients. TensorProduct construction can also collapse intermediate results to zero.
Preserve existing behavior outside the changes currently requested.

Please investigate expansion of additive tensor factors with scalar-weighted summands. I'm unsure whether this input should be explicitly rejected or fully distributed in a single call.

**U1**

When .expand(tensorproduct=True) encounters additive tensor factors whose summands have scalar coefficients, explicitly reject the expansion rather than returning a partially expanded result.

**U2**

Replace the rejection policy with full distribution: a single .expand(tensorproduct=True) call should fully distribute over additive tensor factors even when their summands have scalar coefficients. Preserve correct handling of zero-valued intermediate results.

Update the supplied sympy/sympy repository to meet these requirements:
- Make a single .expand(tensorproduct=True) call fully distribute over additive tensor factors even when their summands have scalar coefficients, while preserving correct handling of zero-valued intermediate results.
Preserve unrelated existing behavior.

## sympy__sympy-24909.source.v1.0fb02a2223

Class: `mixed`; updates: `clarification -> revision`.

**U0**

Work in the supplied sympy/sympy repository. In SymPy's physics units module, multiplying milli by a unit can lose the unit entirely: after importing milli and W, milli*W == 1 returns True. This was observed with watts and volts on SymPy 1.11.1-1.
Preserve existing behavior outside the changes currently requested.

Please investigate how to handle this: should multiplying milli by a unit raise an explicit error, or produce the corresponding milli-scaled unit? I'm unsure which behavior is appropriate.

**U1**

Reject multiplication of milli by a unit with an explicit error so calculations cannot silently proceed with the incorrect value 1.

**U2**

Replace the explicit-error requirement with support for multiplication: milli multiplied by a unit should evaluate to the corresponding milli-scaled unit, such as milliwatts for milli*W, rather than 1.

Update the supplied sympy/sympy repository to meet these requirements:
- Make milli multiplied by a unit evaluate to the corresponding milli-scaled unit, such as milliwatts for milli*W, rather than 1.
Preserve unrelated existing behavior.
