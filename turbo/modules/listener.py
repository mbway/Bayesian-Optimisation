
class Listener:
    """A clean and generic way to gather information from an `Optimiser` as it runs

    Optimiser approximate life-cycle::

        - registered
        - run_started
            - selection_started
                - surrogate_fitted (possibly)
                - acquisition_maximised (possibly)
            - selection_finished
            - evaluation_started
        - evaluation_finished (some time later, others may have started in the meantime)
        - run_finished
        - unregistered

    """
    def registered(self, optimiser):
        """ Called when the listener is registered with the given optimiser """
        pass

    def run_started(self, finished_trials, max_trials):
        """ Called when `Optimiser.run()` is called

        Args:
            finished_trials: the number of trials that were finished prior to this run
            max_trials: the new max_trials as-of starting this run
        """
        pass

    def selection_started(self, trial_num):
        """ Called once the optimiser is looking to select a trial point """
        pass

    def surrogate_fitted(self, trial_num):
        """ Called when the fitting of the surrogate model for the given trial begins

        Note:
            once `maximising_acq()` is called, the surrogate fitting has finished
        """
        pass

    def acquisition_maximised(self, trial_num):
        """ Called when the acquisition function begins maximisation for the given trial

        Note:
            once `trial_started()` is called, the acquisition maximisation has finished
        """
        pass

    def selection_finished(self, trial_num, x, selection_info):
        """ Called when the trial point `x` has been chosen

        Args:
            trial_num: the trial that has just finished the selection phase
            x: the selected input value # TODO: which space?
            selection_info (dict): information about the selection process.
                The specific contents depends on what type of selection
                occurred, which can be determined by the value of
                `selection_info['type']`
        """

    def evaluation_started(self, trial_num):
        """ Called once the trial point `x` has been selected and evaluation will begin """
        pass

    def evaluation_finished(self, trial_num, y, eval_info):
        """ Called once the evaluation for the given trial has finished

        Args:
            trial_num: the trial that has just finished the evaluation phase
            y (float): the cost value returned from the objective function
            eval_info (?): information about the selection process (returned
                from the objective function). None if the objective function
                only returned a cost value.
        """
        pass

    def run_finished(self):
        """ Called when `Optimiser.run()` exits """
        pass

    def unregistered(self):
        """ Called when the listener is unregistered

        The listener will no longer receive messages from the optimiser
        """
        pass
