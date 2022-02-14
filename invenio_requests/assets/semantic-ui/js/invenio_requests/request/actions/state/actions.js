import {
  initRequest
} from '../../../request/state/actions';
import { fetchTimeline } from '../../../timeline/state/actions';

export const IS_LOADING = "requestAction/IS_LOADING";
export const SUCCESS = "requestAction/SUCCESS";
export const HAS_ERROR = "requestAction/HAS_ERROR";
export const ACTION_MODAL_TOGGLE = "requestActionModal/TOGGLE";


export const performAction = (action, commentContent) => {
  return async (dispatch, getState, config) => {
    dispatch({
      type: IS_LOADING,
    });
    try {
      const response = await config.requestsApi.performAction(action, commentContent);
      dispatch({
        type: SUCCESS,
        payload: response.data,
      });
      dispatch(fetchTimeline());
      dispatch(initRequest(response.data));
      dispatch(setActionModalOpen(false, action));
    } catch (error) {
      dispatch({
        type: HAS_ERROR,
        payload: error,
      });
    }
  };
};

export const setActionModalOpen = (isOpen, modalId) => {
  return async (dispatch, getState, config) => {
    dispatch({
      type: ACTION_MODAL_TOGGLE,
      payload: {modalId: modalId, isOpen: isOpen},
    });
  };

}

export const setRefreshInterval = () => {
  return (dispatch, getState, config) => {
    return config.refreshIntervalMs;
  };
};
