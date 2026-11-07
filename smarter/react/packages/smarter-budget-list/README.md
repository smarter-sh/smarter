# Smarter Budgets List React App

This is the source code for the Budgets List app located
at [http://localhost:9357/budget/](http://localhost:9357/budget/).

It lists the budgets that the user may see. Each budget expands to the resources it is attached
to, with their budget versus actual spending this billing period and in total, and a chart of the
last 12 billing periods. Superusers may delete a budget. Budgets are created and changed with
Budget manifests: `smarter apply -f budget.yaml`.

The single-page console, `@smarter/console`, renders this package's `BudgetList` at that path (see
`smarter-console/src/lib/lists.ts`). The package has no build of its own. See also:

- [smarter.apps.account.views.budget.listview](../../../smarter/apps/account/views/budget/listview.py):
  `BudgetListView`, the Django page, a `ConsoleAppView` subclass that keeps the page's url name, and
  `BudgetListApiView`, the list api.

## Development

```console
cd smarter/react
npm run dev -w @smarter/budget-list     # http://localhost:5173/, against the Django dev server at :9357
npm run test -w @smarter/budget-list
```
